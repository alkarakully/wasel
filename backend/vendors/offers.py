"""Offer rules shared by the store portal and the platform admin."""

from decimal import Decimal

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers

from regions.regions import as_api, quantize, region
from regions.serializers import check_amount

from .models import Offer


def check_offer(data, instance, country, store=None):
    """Validates an offer's dates and amounts in `country`'s currency; raises ValidationError."""
    currency = region(country).currency

    def current(key, default=None):
        return data.get(key, getattr(instance, key, default))

    if current("type") == Offer.Type.BOGO:
        product = current("product")
        if store is None:
            raise serializers.ValidationError({"type": "Buy one, get one free is for one store's item."})
        if product is None or product.vendor_id != store.pk or product.is_archived:
            raise serializers.ValidationError({"product": "Choose an item from this store's menu."})
        if product.unit_type != product.UnitType.ITEM:
            raise serializers.ValidationError({"product": "Pick an item sold by the piece, not by weight."})
        # One deal per item at a time, so it's clear which one applies.
        starts, ends = current("starts_at"), current("ends_at")
        overlapping = Offer.objects.filter(
            type=Offer.Type.BOGO, product=product, starts_at__lt=ends, ends_at__gt=starts
        ).exclude(pk=getattr(instance, "pk", None))
        if starts and ends and overlapping.exists():
            raise serializers.ValidationError({"product": "This item already has a buy one, get one free deal then."})
        data["value"] = Decimal(0)
    else:
        data["product"] = None

    starts, ends = current("starts_at"), current("ends_at")
    if starts and ends and ends <= starts:
        raise serializers.ValidationError({"ends_at": "End after it starts."})
    kind, value = current("type"), current("value", 0)
    if kind == Offer.Type.PERCENT and not (0 < value <= 100):
        raise serializers.ValidationError({"value": "A percentage from 1 to 100."})
    if kind == Offer.Type.FIXED and value <= 0:
        raise serializers.ValidationError({"value": "Enter an amount above zero."})
    try:
        if kind == Offer.Type.FIXED:
            check_amount(value, currency)
        check_amount(current("min_order", 0), currency)
    except serializers.ValidationError as error:
        field = "value" if kind == Offer.Type.FIXED and value != quantize(value, currency) else "min_order"
        raise serializers.ValidationError({field: error.detail}) from error


def offer_state(offer, now=None):
    now = now or timezone.now()
    return "scheduled" if offer.starts_at > now else "ended" if offer.ends_at <= now else "running"


def offer_value(offer):
    """A fixed offer's value is money; a percent stays a plain number."""
    if offer.type == Offer.Type.FIXED:
        return as_api(offer.value, offer.currency)
    return f"{offer.value.normalize():f}"


def times_used(offers):
    """`offers` annotated with order_count: orders it was the offer of, or had one of its item deals."""
    return offers.annotate(
        order_count=Count("orders", distinct=True) + Count("order_items__order", distinct=True)
    )


def end_or_delete(offer):
    """An offer nobody used is deleted; a used one ends now, so old orders keep it. Returns "ended" or "deleted"."""
    if offer.orders.exists() or offer.order_items.exists():
        offer.ends_at = min(offer.ends_at, timezone.now())
        offer.save(update_fields=["ends_at"])
        return "ended"
    offer.delete()
    return "deleted"
