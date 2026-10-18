"""
Pushes order changes to everyone involved over WebSockets.

Groups:
  user-<id>     a signed-in user's own orders (as customer or captain)
  vendor-<id>   orders for a store, joined by its owner
  captains      orders waiting for a captain
  support       staff users: stuck-order alerts

Messages sent to clients:
  {"type": "order.updated", "order": {...}}      the full order, as from the REST API
  {"type": "order.available", "order": {...}}    captains: a store accepted an order with no captain
  {"type": "order.unavailable", "order_id": 12}  captains: claimed or cancelled, drop it from the list
  {"type": "order.stuck", "alert": {...}}        support: an order has sat in one step too long
  {"type": "captain.location", "order_id": 12, "location": {...}}
                                                 customer and store: where the order's captain is now
  {"type": "dispatch.offer", "offer": {...}}     one captain: take this order? (expires_at)
  {"type": "dispatch.offer_closed", "offer_id": 3, "reason": "expired"}
                                                 that captain: the offer is no longer open
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Order
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)

CAPTAINS_GROUP = "captains"
SUPPORT_GROUP = "support"


def user_group(user_id):
    return f"user-{user_id}"


def vendor_group(vendor_id):
    return f"vendor-{vendor_id}"


def _send(group, payload):
    async_to_sync(get_channel_layer().group_send)(group, {"type": "order.event", "payload": payload})


def _order_data(order):
    # No request in context, so the delivery PIN serializes as None.
    return OrderSerializer(order).data


def _broadcast(order_id, was_available):
    order = Order.objects.select_related("vendor", "captain__location").prefetch_related("items__product", "items__modifiers__modifier").get(pk=order_id)
    data = _order_data(order)

    # Only the customer gets the PIN; they read it to the captain at the door.
    _send(user_group(order.customer_id), {"type": "order.updated", "order": {**data, "delivery_pin": order.delivery_pin}})
    _send(vendor_group(order.vendor_id), {"type": "order.updated", "order": data})
    if order.captain_id:
        _send(user_group(order.captain_id), {"type": "order.updated", "order": data})

    # While dispatch is offering the order to one captain, the others don't see it.
    available = order.in_open_pool()
    if available and not was_available:
        _send(CAPTAINS_GROUP, {"type": "order.available", "order": data})
    elif was_available and not available:
        _send(CAPTAINS_GROUP, {"type": "order.unavailable", "order_id": order.pk})


def was_available(order):
    return order.in_open_pool()


def _safe_broadcast(order_id, was_available):
    # The order change is already saved; a Redis hiccup must not turn it into an error.
    try:
        _broadcast(order_id, was_available)
    except Exception:
        logger.exception("Could not send live update for order %s", order_id)


def broadcast_order(order_id, was_available=False):
    """Send the order to everyone involved once the current transaction commits."""
    transaction.on_commit(lambda: _safe_broadcast(order_id, was_available))


def send_stuck_alert(alert):
    try:
        _send(
            SUPPORT_GROUP,
            {
                "type": "order.stuck",
                "alert": {
                    "id": alert.pk,
                    "order_id": alert.order_id,
                    "reason": alert.reason,
                    "reason_label": alert.get_reason_display(),
                    "created_at": alert.created_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception("Could not send stuck-order alert %s", alert.pk)


def notify_user(user_id, payload):
    """Send an app-level event (not an order update) to one user's sockets."""
    try:
        _send(user_group(user_id), payload)
    except Exception:
        logger.exception("Could not notify user %s", user_id)


def send_captain_location(order_id, customer_id, vendor_id, location):
    payload = {"type": "captain.location", "order_id": order_id, "location": location}
    try:
        _send(user_group(customer_id), payload)
        _send(vendor_group(vendor_id), payload)
    except Exception:
        logger.exception("Could not send captain location for order %s", order_id)


def announce_open(order_id):
    """Dispatch found nobody: show the order to every captain."""

    def send():
        order = Order.objects.select_related("vendor").prefetch_related("items__product", "items__modifiers__modifier").get(pk=order_id)
        if order.in_open_pool():
            _send(CAPTAINS_GROUP, {"type": "order.available", "order": _order_data(order)})

    transaction.on_commit(lambda: _guard(send, "announce order %s" % order_id))


def send_offer(offer):
    order = (
        Order.objects.select_related("vendor")
        .prefetch_related("items__product", "items__modifiers__modifier")
        .get(pk=offer.order_id)
    )
    _guard(
        lambda: _send(
            user_group(offer.captain_id),
            {
                "type": "dispatch.offer",
                "offer": {
                    "id": offer.pk,
                    "order": _order_data(order),
                    "distance_km": round(offer.distance_m / 1000, 2),
                    "expires_at": offer.expires_at.isoformat(),
                },
            },
        ),
        "send dispatch offer %s" % offer.pk,
    )


def send_offer_closed(offer, reason):
    _guard(
        lambda: _send(user_group(offer.captain_id), {"type": "dispatch.offer_closed", "offer_id": offer.pk, "reason": reason}),
        "close dispatch offer %s" % offer.pk,
    )


def _guard(action, what):
    try:
        action()
    except Exception:
        logger.exception("Could not %s", what)
