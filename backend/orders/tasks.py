"""Periodic checks that flag orders sitting too long in one step."""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Order, StuckOrderAlert
from .realtime import send_stuck_alert

logger = logging.getLogger(__name__)

Reason = StuckOrderAlert.Reason


def stuck_orders(now):
    """Yield (order_id, reason) for every order that is stuck right now."""
    limit = {reason: timedelta(minutes=minutes) for reason, minutes in settings.STUCK_ORDER_MINUTES.items()}
    S = Order.Status
    checks = {
        Reason.NOT_ACCEPTED: Order.objects.filter(status=S.RECEIVED, created_at__lt=now - limit["not_accepted"]),
        Reason.NOT_READY: Order.objects.filter(status=S.PREPARING, estimated_ready_at__lt=now - limit["not_ready"]),
        Reason.NO_CAPTAIN: Order.objects.filter(
            status__in=[S.PREPARING, S.READY], captain__isnull=True, accepted_at__lt=now - limit["no_captain"]
        ),
        Reason.NOT_PICKED_UP: Order.objects.filter(
            status=S.READY, captain__isnull=False, ready_at__lt=now - limit["not_picked_up"]
        ),
        Reason.DELIVERY_LATE: Order.objects.filter(
            status=S.OUT_FOR_DELIVERY, picked_up_at__lt=now - limit["delivery_late"]
        ),
    }
    for reason, orders in checks.items():
        for order_id in orders.values_list("pk", flat=True):
            yield order_id, reason


@shared_task
def flag_stuck_orders():
    """Open an alert for each newly stuck order and close alerts for orders that moved on."""
    now = timezone.now()
    stuck = set(stuck_orders(now))

    open_alerts = {(a.order_id, a.reason): a for a in StuckOrderAlert.objects.filter(resolved_at__isnull=True)}

    resolved = [a.pk for key, a in open_alerts.items() if key not in stuck]
    StuckOrderAlert.objects.filter(pk__in=resolved).update(resolved_at=now)

    created = 0
    for order_id, reason in stuck - open_alerts.keys():
        try:
            with transaction.atomic():
                alert = StuckOrderAlert.objects.create(order_id=order_id, reason=reason)
        except IntegrityError:
            continue  # another run opened it at the same moment
        created += 1
        send_stuck_alert(alert)

    if created or resolved:
        logger.warning("Stuck orders: %d new alerts, %d resolved", created, len(resolved))
    return {"created": created, "resolved": len(resolved)}
