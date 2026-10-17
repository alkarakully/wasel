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
    order = Order.objects.select_related("vendor").prefetch_related("items__modifiers").get(pk=order_id)
    data = _order_data(order)

    # Only the customer gets the PIN; they read it to the captain at the door.
    _send(user_group(order.customer_id), {"type": "order.updated", "order": {**data, "delivery_pin": order.delivery_pin}})
    _send(vendor_group(order.vendor_id), {"type": "order.updated", "order": data})
    if order.captain_id:
        _send(user_group(order.captain_id), {"type": "order.updated", "order": data})

    available = order.captain_id is None and order.status in (Order.Status.PREPARING, Order.Status.READY)
    if available and not was_available:
        _send(CAPTAINS_GROUP, {"type": "order.available", "order": data})
    elif was_available and not available:
        _send(CAPTAINS_GROUP, {"type": "order.unavailable", "order_id": order.pk})


def was_available(order):
    return order.captain_id is None and order.status in (Order.Status.PREPARING, Order.Status.READY)


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
