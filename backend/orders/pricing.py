"""
Order pricing: one place that turns a cart into the full price breakdown.

The quote endpoint and order placement both use build_quote(), so the price
a customer sees before ordering is exactly what they are charged.

  total = subtotal + delivery_fee + service_fee + tip - discount

Commission is charged on the food subtotal. When the vendor funds a discount
(a percent or fixed offer on their own store) commission is charged on the
discounted subtotal; platform-wide offers are funded by Wasel and don't
reduce the vendor's commission.
"""

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q
from django.utils import timezone

from subscriptions.models import WaselPlusSubscription
from vendors.models import Offer, Product, Vendor


class PricingError(Exception):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class QuoteLine:
    product: Product
    quantity: Decimal
    modifiers: list
    unit_price: Decimal
    line_total: Decimal


@dataclass
class Quote:
    vendor: Vendor
    distance_m: float
    lines: list = field(default_factory=list)
    subtotal: Decimal = Decimal(0)
    delivery_fee: Decimal = Decimal(0)
    service_fee: Decimal = Decimal(0)
    discount: Decimal = Decimal(0)
    tip: Decimal = Decimal(0)
    commission_amount: Decimal = Decimal(0)
    total_amount: Decimal = Decimal(0)
    offer: Offer = None
    wasel_plus: bool = False


def _config(key):
    return settings.ORDER_PRICING[key]


def round_dinars(amount):
    return Decimal(amount).quantize(Decimal(1), rounding=ROUND_HALF_UP)


def _round_up(amount, step):
    return Decimal(math.ceil(Decimal(amount) / step) * step)


def delivery_fee_for(distance_m):
    """Base fee for the first few km, then a fee per started km, rounded up."""
    extra_km = max(0, math.ceil(Decimal(distance_m) / 1000 - _config("DELIVERY_BASE_KM")))
    fee = _config("DELIVERY_BASE_FEE") + extra_km * _config("DELIVERY_FEE_PER_KM")
    return _round_up(fee, _config("FEE_ROUNDING"))


def has_wasel_plus(user, at):
    return (
        WaselPlusSubscription.objects.filter(user=user)
        .filter(
            Q(status=WaselPlusSubscription.Status.ACTIVE)
            | Q(status=WaselPlusSubscription.Status.TRIAL, trial_end_date__gt=at)
        )
        .exists()
    )


def offer_discount(offer, subtotal, delivery_fee):
    """Discount this offer gives on the cart, or None if it doesn't apply."""
    if subtotal < offer.min_order:
        return None
    if offer.type == Offer.Type.PERCENT:
        return min(round_dinars(subtotal * offer.value / 100), subtotal)
    if offer.type == Offer.Type.FIXED:
        return min(round_dinars(offer.value), subtotal)
    if offer.type == Offer.Type.FREE_DELIVERY:
        return delivery_fee if delivery_fee > 0 else None
    # Bundle deals need a bundle definition, which isn't modelled yet.
    return None


def _price_lines(vendor, items):
    if not items:
        raise PricingError("empty_cart", "Add at least one item.")

    product_ids = {item["product"] for item in items}
    products = {
        product.pk: product
        for product in Product.objects.filter(vendor=vendor, pk__in=product_ids, is_archived=False).prefetch_related(
            "modifiers"
        )
    }

    lines = []
    for item in items:
        product = products.get(item["product"])
        if product is None:
            raise PricingError("product_not_found", f"Product {item['product']} is not on this vendor's menu.")
        if not product.is_available:
            raise PricingError("product_unavailable", f"{product} is out of stock.")

        quantity = Decimal(item.get("quantity", 1))
        if product.unit_type == Product.UnitType.KG:
            if not 0 < quantity <= _config("MAX_KG"):
                raise PricingError("invalid_quantity", f"Choose between 0 and {_config('MAX_KG')} kg of {product}.")
        elif quantity != quantity.to_integral_value() or not 1 <= quantity <= _config("MAX_ITEM_QUANTITY"):
            raise PricingError(
                "invalid_quantity", f"Quantity of {product} must be a whole number from 1 to {_config('MAX_ITEM_QUANTITY')}."
            )

        available = {modifier.pk: modifier for modifier in product.modifiers.all()}
        chosen_ids = list(dict.fromkeys(item.get("modifiers", [])))
        unknown = [pk for pk in chosen_ids if pk not in available]
        if unknown:
            raise PricingError("invalid_modifier", f"Option {unknown[0]} is not available for {product}.")
        chosen = [available[pk] for pk in chosen_ids]

        required_groups = {m.group_name for m in available.values() if m.is_required}
        missing = required_groups - {m.group_name for m in chosen}
        if missing:
            raise PricingError("missing_required_option", f"Choose a {sorted(missing)[0]} for {product}.")

        unit_price = product.price + sum((m.price_delta for m in chosen), Decimal(0))
        lines.append(
            QuoteLine(
                product=product,
                quantity=quantity,
                modifiers=chosen,
                unit_price=unit_price,
                line_total=round_dinars(unit_price * quantity),
            )
        )
    return lines


def _pick_offer(vendor, offer_id, subtotal, delivery_fee, at):
    running = Offer.objects.filter(starts_at__lte=at, ends_at__gte=at).filter(Q(vendor=vendor) | Q(vendor__isnull=True))

    if offer_id is not None:
        offer = running.filter(pk=offer_id).first()
        discount = offer_discount(offer, subtotal, delivery_fee) if offer else None
        if not discount:
            raise PricingError("offer_not_applicable", "This offer can't be used on this order.")
        return offer, discount

    # No offer chosen: apply the best one the cart qualifies for.
    best, best_discount = None, Decimal(0)
    for offer in running:
        discount = offer_discount(offer, subtotal, delivery_fee) or Decimal(0)
        if discount > best_discount:
            best, best_discount = offer, discount
    return best, best_discount


def build_quote(customer, vendor_id, items, delivery_point, offer_id=None, tip=0, at=None):
    at = at or timezone.now()

    vendor = Vendor.objects.annotate(distance=Distance("location", delivery_point)).filter(pk=vendor_id).first()
    if vendor is None:
        raise PricingError("vendor_not_found", "This store doesn't exist.")
    if not vendor.is_open:
        raise PricingError("vendor_closed", f"{vendor} is closed right now.")
    distance_m = vendor.distance.m
    if distance_m > float(vendor.delivery_radius_km) * 1000:
        raise PricingError("out_of_delivery_area", f"{vendor} doesn't deliver to this location.")

    tip = Decimal(tip)
    if not 0 <= tip <= _config("MAX_TIP"):
        raise PricingError("invalid_tip", f"Tip must be between 0 and {_config('MAX_TIP')} IQD.")

    quote = Quote(vendor=vendor, distance_m=distance_m, tip=round_dinars(tip))
    quote.lines = _price_lines(vendor, items)
    quote.subtotal = sum((line.line_total for line in quote.lines), Decimal(0))

    quote.wasel_plus = has_wasel_plus(customer, at)
    if quote.wasel_plus and quote.subtotal >= _config("PLUS_FREE_DELIVERY_MIN"):
        quote.delivery_fee = Decimal(0)
    else:
        quote.delivery_fee = delivery_fee_for(distance_m)
    quote.service_fee = Decimal(_config("PLUS_SERVICE_FEE") if quote.wasel_plus else _config("SERVICE_FEE"))

    quote.offer, quote.discount = _pick_offer(vendor, offer_id, quote.subtotal, quote.delivery_fee, at)

    vendor_funded = quote.offer is not None and quote.offer.vendor_id is not None and quote.offer.type in (
        Offer.Type.PERCENT,
        Offer.Type.FIXED,
    )
    commission_base = quote.subtotal - quote.discount if vendor_funded else quote.subtotal
    quote.commission_amount = vendor.commission_for(commission_base, at)

    quote.total_amount = quote.subtotal + quote.delivery_fee + quote.service_fee + quote.tip - quote.discount
    return quote
