"""
Weekly statements: Saturday to Friday in Baghdad, which is how Iraqi
businesses count the week.
"""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from orders.models import Order
from vendors.models import Vendor
from vendors.reports import store_payout

from .models import Statement

SATURDAY = 5  # date.weekday()


def week_start(day):
    """The Saturday that starts the week holding `day`."""
    return day - timedelta(days=(day.weekday() - SATURDAY) % 7)


def week_orders(vendor, start):
    """Delivered orders of the store in the week starting `start` (by delivery time)."""
    tz = timezone.get_current_timezone()
    since = timezone.make_aware(datetime.combine(start, time.min), tz)
    until = since + timedelta(days=7)
    return Order.objects.filter(
        vendor=vendor, status=Order.Status.DELIVERED, delivered_at__gte=since, delivered_at__lt=until
    )


def week_figures(vendor, start):
    orders = week_orders(vendor, start)
    return {"orders_count": orders.count(), **store_payout(orders)}


@transaction.atomic
def close_week(start):
    """
    Make the statements for one finished week; stores without delivered
    orders that week get none. Safe to run again: existing ones are kept.
    """
    made = []
    end = start + timedelta(days=6)
    for vendor in Vendor.objects.all():
        if Statement.objects.filter(vendor=vendor, period_start=start).exists():
            continue
        figures = week_figures(vendor, start)
        if not figures["orders_count"]:
            continue
        made.append(Statement.objects.create(vendor=vendor, period_start=start, period_end=end, **figures))
    return made


def close_finished_weeks(weeks_back=8):
    """Close every finished week in the last few that hasn't been closed (catches up after downtime)."""
    current = week_start(timezone.localdate())
    made = []
    for n in range(weeks_back, 0, -1):
        made += close_week(current - timedelta(weeks=n))
    return made
