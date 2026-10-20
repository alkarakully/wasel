"""
Order pricing: one place that turns a cart into the full price breakdown.

The quote endpoint and order placement both use build_quote(), so the price
a customer sees before ordering is exactly what they are charged.

  total = subtotal + delivery_fee + service_fee + tip - discount

The discount has two parts:

  item deals   each item with a running buy-one-get-one-free offer: every
               second unit is free (the cheaper ones when options differ).
               Several items can each have their own deal in one order.
  order offer  at most one percent, fixed or free-delivery offer, the best the
               cart qualifies for after item deals (or the one the customer
               picked). It's worked out on the food left to pay for.

Who pays: the store pays for deals on its own items and for its own offers
(store_discount, taken from its payout); Wasel pays for platform-wide offers.

Commission is charged on the food subtotal less what the store gives away on
food (item deals and its percent or fixed offers). A store's free-delivery
offer doesn't touch food, so it doesn't lower commission.
"""

import math
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q
from django.utils import timezone

from regions.regions import quantize, region
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
    # Buy one, get one free on this line's item: the deal and what it takes off.
    deal: Offer = None
    discount: Decimal = Decimal(0)


@dataclass
class Quote:
    vendor: Vendor
    distance_m: float
    lines: list = field(default_factory=list)
    subtotal: Decimal = Decimal(0)
    delivery_fee: Decimal = Decimal(0)
    service_fee: Decimal = Decimal(0)
    # Item deals plus the order offer; store_discount is the part the store pays.
    discount: Decimal = Decimal(0)
    items_discount: Decimal = Decimal(0)
    store_discount: Decimal = Decimal(0)
    tip: Decimal = Decimal(0)
    commission_amount: Decimal = Decimal(0)
    total_amount: Decimal = Decimal(0)
    offer: Offer = None
    wasel_plus: bool = False


def _config(key):
    return settings.ORDER_PRICING[key]


def _price(country, key):
    """A fee or limit for the store's country, in its currency."""
    return region(country).pricing[key]


def _round_up(amount, step):
    return Decimal(math.ceil(Decimal(amount) / step)) * step


def delivery_fee_for(distance_m, country="IQ"):
    """Base fee for the first few km, then a fee per started km, rounded up to the country's step."""
    extra_km = max(0, math.ceil(Decimal(distance_m) / 1000 - _price(country, "DELIVERY_BASE_KM")))
    fee = _price(country, "DELIVERY_BASE_FEE") + extra_km * _price(country, "DELIVERY_FEE_PER_KM")
    return quantize(_round_up(fee, _price(country, "FEE_ROUNDING")), region(country).currency)


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
    """What an order offer takes off `subtotal` (the food still to pay for), or None if it doesn't apply."""
    if subtotal < offer.min_order:
        return None
    if offer.type == Offer.Type.PERCENT:
        return min(quantize(subtotal * offer.value / 100, offer.currency), subtotal)
    if offer.type == Offer.Type.FIXED:
        return min(quantize(offer.value, offer.currency), subtotal)
    if offer.type == Offer.Type.FREE_DELIVERY:
        return delivery_fee if delivery_fee > 0 else None
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
                line_total=quantize(unit_price * quantity, vendor.currency),
            )
        )
    return lines


def apply_item_deals(vendor, lines, subtotal, at):
    """
    Puts each running buy-one-get-one-free deal on its item's lines and returns the total.

    Every second unit of the item is free, and when the units differ (other
    options), the cheaper ones are the free ones. Only items sold by the
    piece count: half a kilo free isn't a thing.
    """
    by_item = {}
    deals = Offer.objects.filter(
        vendor=vendor, type=Offer.Type.BOGO, starts_at__lte=at, ends_at__gte=at, product__isnull=False
    ).order_by("starts_at", "pk")
    for deal in deals:
        by_item.setdefault(deal.product_id, deal)  # one deal per item; the oldest wins

    total = Decimal(0)
    for product_id, deal in by_item.items():
        if subtotal < deal.min_order:
            continue
        mine = [line for line in lines if line.product.pk == product_id and line.product.unit_type == Product.UnitType.ITEM]
        units = sorted((line.unit_price, i) for i, line in enumerate(mine) for _ in range(int(line.quantity)))
        for price, i in units[: len(units) // 2]:
            mine[i].deal = deal
            mine[i].discount += price
        total += sum((line.discount for line in mine), Decimal(0))
    for line in lines:
        line.discount = quantize(line.discount, vendor.currency)
    return quantize(total, vendor.currency)


def _pick_offer(vendor, offer_id, subtotal, delivery_fee, at):
    # The store's own offers, and Wasel's offers for the store's country (in its currency).
    # Buy-one-get-one deals are per item and handled by apply_item_deals().
    running = Offer.objects.filter(starts_at__lte=at, ends_at__gte=at).exclude(type=Offer.Type.BOGO).filter(
        Q(vendor=vendor) | Q(vendor__isnull=True, country=vendor.country)
    )

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

    # Stores waiting for approval don't exist as far as customers can tell.
    vendor = (
        Vendor.objects.annotate(distance=Distance("location", delivery_point))
        .filter(pk=vendor_id, status=Vendor.Status.APPROVED)
        .first()
    )
    if vendor is None:
        raise PricingError("vendor_not_found", "This store doesn't exist.")
    if not vendor.is_open:
        raise PricingError("vendor_closed", f"{vendor} is closed right now.")
    distance_m = vendor.distance.m
    if distance_m > float(vendor.delivery_radius_km) * 1000:
        raise PricingError("out_of_delivery_area", f"{vendor} doesn't deliver to this location.")

    country, currency = vendor.country, vendor.currency
    tip = Decimal(tip)
    if not 0 <= tip <= _price(country, "MAX_TIP"):
        raise PricingError("invalid_tip", f"Tip must be between 0 and {_price(country, 'MAX_TIP')} {currency}.")

    quote = Quote(vendor=vendor, distance_m=distance_m, tip=quantize(tip, currency))
    quote.lines = _price_lines(vendor, items)
    quote.subtotal = sum((line.line_total for line in quote.lines), Decimal(0))

    quote.wasel_plus = has_wasel_plus(customer, at)
    if quote.wasel_plus and quote.subtotal >= _price(country, "PLUS_FREE_DELIVERY_MIN"):
        quote.delivery_fee = Decimal(0)
    else:
        quote.delivery_fee = delivery_fee_for(distance_m, country)
    quote.service_fee = _price(country, "PLUS_SERVICE_FEE" if quote.wasel_plus else "SERVICE_FEE")

    quote.items_discount = apply_item_deals(vendor, quote.lines, quote.subtotal, at)
    food_left = quote.subtotal - quote.items_discount
    quote.offer, order_discount = _pick_offer(vendor, offer_id, food_left, quote.delivery_fee, at)
    quote.discount = quote.items_discount + order_discount

    store_offer = quote.offer is not None and quote.offer.vendor_id is not None
    quote.store_discount = quote.items_discount + (order_discount if store_offer else Decimal(0))
    store_food_offer = store_offer and quote.offer.type in (Offer.Type.PERCENT, Offer.Type.FIXED)
    commission_base = food_left - (order_discount if store_food_offer else Decimal(0))
    quote.commission_amount = vendor.commission_for(commission_base, at)

    quote.total_amount = quote.subtotal + quote.delivery_fee + quote.service_fee + quote.tip - quote.discount
    return quote
