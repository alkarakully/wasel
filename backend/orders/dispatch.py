"""
Automatic captain dispatch.

When a store accepts an order it is offered to the nearest free captain, who
has a few seconds to accept. A decline or timeout moves the offer to the next
nearest captain. When nobody suitable is left the order goes to the open list
that every captain can see, as before.

A captain is a candidate when they are online, have a recent GPS fix within
the radius of the store, aren't carrying another order, and haven't already
been offered this one.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from notifications.push import notify

from . import realtime, workflow
from .models import TRACKED_STATUSES, CaptainLocation, DispatchOffer, Order
from .tasks import expire_dispatch_offer

logger = logging.getLogger(__name__)


class OfferGone(Exception):
    """The offer was answered, timed out or withdrawn before this response."""


def _config(key):
    return settings.DISPATCH[key]


def candidates(order, now=None):
    """Free captains near the store, nearest first."""
    now = now or timezone.now()
    already_offered = DispatchOffer.objects.filter(order=order).values("captain_id")
    busy = Order.objects.filter(status__in=TRACKED_STATUSES, captain__isnull=False).values("captain_id")
    return (
        CaptainLocation.objects.filter(
            is_online=True,
            point__isnull=False,
            captain__role=User.Role.CAPTAIN,
            captain__is_active=True,
            updated_at__gte=now - timedelta(minutes=_config("STALE_MINUTES")),
            point__dwithin=(order.vendor.location, D(km=_config("RADIUS_KM"))),
        )
        .exclude(captain_id__in=already_offered)
        .exclude(captain_id__in=busy)
        .annotate(distance=Distance("point", order.vendor.location))
        .order_by("distance")
    )


def offer_next(order_id, announce_if_none=True):
    """
    Offer the order to the next nearest free captain. Returns the offer, or None
    when nobody is left (the order then joins the open list; `announce_if_none`
    tells captains about it, unless the caller broadcasts anyway).
    """
    now = timezone.now()
    with transaction.atomic():
        order = Order.objects.select_for_update(of=("self",)).select_related("vendor").get(pk=order_id)
        if not order.waiting_for_captain or order.pending_offer():
            return None
        captain = candidates(order, now).select_related("captain").first()
        if captain is None:
            if announce_if_none:
                realtime.announce_open(order.pk)
            return None
        offer = DispatchOffer.objects.create(
            order=order,
            captain_id=captain.captain_id,
            distance_m=captain.distance.m,
            expires_at=now + timedelta(seconds=_config("OFFER_SECONDS")),
        )
        transaction.on_commit(lambda: _after_offer(offer.pk))
    return offer


def _after_offer(offer_id):
    offer = DispatchOffer.objects.select_related("order__vendor").get(pk=offer_id)
    realtime.send_offer(offer)
    # Reaches the captain even when the app is in the background or closed.
    notify(
        offer.captain_id,
        "captain",
        "offer",
        offer_id=offer.pk,
        order_id=offer.order_id,
        store=offer.order.vendor.name,
        km=f"{offer.distance_m / 1000:.1f}",
        seconds=settings.DISPATCH["OFFER_SECONDS"],
    )
    # Expire it on time even if the captain's app never answers.
    try:
        expire_dispatch_offer.apply_async((offer.pk,), eta=offer.expires_at + timedelta(seconds=1))
    except Exception:
        # The periodic sweep picks it up instead.
        logger.exception("Could not schedule expiry for dispatch offer %s", offer.pk)


def _lock_pending(offer_id, captain):
    offer = DispatchOffer.objects.select_for_update().filter(pk=offer_id).first()
    if offer is None or offer.captain_id != captain.pk:
        raise OfferGone("This offer isn't yours.")
    if offer.status != DispatchOffer.Status.PENDING or offer.expires_at <= timezone.now():
        raise OfferGone("This offer has ended.")
    return offer


def accept(offer_id, captain):
    """The captain takes the order. Returns the order."""
    with transaction.atomic():
        offer = _lock_pending(offer_id, captain)
        # claim() marks this captain's pending offer as accepted.
        return workflow.claim(offer.order_id, captain)


def decline(offer_id, captain):
    with transaction.atomic():
        offer = _lock_pending(offer_id, captain)
        offer.status = DispatchOffer.Status.DECLINED
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at"])
    offer_next(offer.order_id)


def expire(offer_id):
    """Time's up: close the offer and move on. Safe to call more than once."""
    with transaction.atomic():
        offer = DispatchOffer.objects.select_for_update().filter(pk=offer_id).first()
        if offer is None or offer.status != DispatchOffer.Status.PENDING or offer.expires_at > timezone.now():
            return False
        offer.status = DispatchOffer.Status.EXPIRED
        offer.save(update_fields=["status"])
        transaction.on_commit(lambda: realtime.send_offer_closed(offer, "expired"))
    offer_next(offer.order_id)
    return True


def withdraw(order_id, reason):
    """The order was cancelled or taken another way: close any running offer."""
    for offer in DispatchOffer.objects.filter(order_id=order_id, status=DispatchOffer.Status.PENDING):
        offer.status = DispatchOffer.Status.CANCELLED
        offer.save(update_fields=["status"])
        transaction.on_commit(lambda offer=offer: realtime.send_offer_closed(offer, reason))
