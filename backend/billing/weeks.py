"""
Weekly statements, on each store's own calendar: the week starts on the day
its country starts the business week (Saturday in Iraq, Sunday in most of
the Gulf, Monday in the Emirates) and days end at midnight where it is.
"""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from orders.models import Order
from regions.regions import CODES, region
from vendors.models import Vendor
from vendors.reports import store_payout

from .models import Statement


def week_start(day, country="IQ"):
    """The first day of the country's business week holding `day`."""
    return day - timedelta(days=(day.weekday() - region(country).week_starts) % 7)


def local_today(country="IQ"):
    return timezone.localdate(timezone=region(country).tz)


def week_orders(vendor, start):
    """Delivered orders of the store in the week starting `start` (by delivery time, in the store's time zone)."""
    since = timezone.make_aware(datetime.combine(start, time.min), vendor.tz)
    until = timezone.make_aware(datetime.combine(start + timedelta(days=7), time.min), vendor.tz)
    return Order.objects.filter(
        vendor=vendor, status=Order.Status.DELIVERED, delivered_at__gte=since, delivered_at__lt=until
    )


def week_figures(vendor, start):
    orders = week_orders(vendor, start)
    return {"orders_count": orders.count(), **store_payout(orders)}


@transaction.atomic
def close_week(start, country="IQ"):
    """
    Make the statements for one finished week of the country's stores; stores
    without delivered orders that week get none. Safe to run again: existing
    ones are kept.
    """
    made = []
    end = start + timedelta(days=6)
    for vendor in Vendor.objects.filter(country=country):
        if Statement.objects.filter(vendor=vendor, period_start=start).exists():
            continue
        figures = week_figures(vendor, start)
        if not figures["orders_count"]:
            continue
        made.append(
            Statement.objects.create(
                vendor=vendor, period_start=start, period_end=end, currency=vendor.currency, **figures
            )
        )
    return made


def close_finished_weeks(weeks_back=8):
    """Close every finished week in the last few, in every country (catches up after downtime)."""
    made = []
    for country in CODES:
        current = week_start(local_today(country), country)
        for n in range(weeks_back, 0, -1):
            made += close_week(current - timedelta(weeks=n), country)
    return made
