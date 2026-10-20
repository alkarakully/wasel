"""Offer rules shared by the store portal and the platform admin."""

from django.utils import timezone
from rest_framework import serializers

from regions.regions import as_api, quantize, region
from regions.serializers import check_amount

from .models import Offer


def check_offer(data, instance, country):
    """Validates an offer's dates and amounts in `country`'s currency; raises ValidationError."""
    currency = region(country).currency

    def current(key, default=None):
        return data.get(key, getattr(instance, key, default))

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


def end_or_delete(offer):
    """An offer nobody used is deleted; a used one ends now, so old orders keep it. Returns "ended" or "deleted"."""
    if offer.orders.exists():
        offer.ends_at = min(offer.ends_at, timezone.now())
        offer.save(update_fields=["ends_at"])
        return "ended"
    offer.delete()
    return "deleted"
