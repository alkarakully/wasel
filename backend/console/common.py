from datetime import datetime, time

from django.db.models import Avg, DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from orders.models import Order
from regions.regions import CODES, as_api, region

ACTIVE = [Order.Status.RECEIVED, Order.Status.PREPARING, Order.Status.READY, Order.Status.OUT_FOR_DELIVERY]


def country_param(request):
    """
    The operating country platform numbers are for (?country=, Iraq by
    default): sums stay in one currency and days follow one clock.
    """
    code = (request.query_params.get("country") or "IQ").upper()
    return code if code in CODES else "IQ"


def local_today(country="IQ"):
    return timezone.localdate(timezone=region(country).tz)


def start_of(day, country="IQ"):
    """Start of a calendar day in the country, as an aware datetime."""
    return timezone.make_aware(datetime.combine(day, time.min), region(country).tz)


def money(value, currency="IQD"):
    """An amount for JSON, with exactly its currency's decimals."""
    return as_api(value, currency)


def iso(value):
    return value.isoformat() if value else None


def person(user):
    return {"id": user.pk, "name": user.name, "phone": user.phone} if user else None


def figures(orders, currency="IQD"):
    """Order counts and money for a set of orders in one currency (cancelled ones earn nothing)."""
    earning = orders.exclude(status=Order.Status.CANCELLED)
    sums = earning.aggregate(
        sales=Sum("total_amount"),
        commission=Sum("commission_amount"),
        service_fees=Sum("service_fee"),
        delivery_fees=Sum("delivery_fee"),
        discounts=Sum("discount"),
    )
    delivered = orders.filter(status=Order.Status.DELIVERED, delivered_at__isnull=False)
    avg = delivered.aggregate(
        avg=Avg(ExpressionWrapper(F("delivered_at") - F("created_at"), output_field=DurationField()))
    )["avg"]
    return {
        "orders": orders.count(),
        "delivered": delivered.count(),
        "cancelled": orders.filter(status=Order.Status.CANCELLED).count(),
        "sales": money(sums["sales"], currency),
        "commission": money(sums["commission"], currency),
        "service_fees": money(sums["service_fees"], currency),
        "delivery_fees": money(sums["delivery_fees"], currency),
        "discounts": money(sums["discounts"], currency),
        "avg_delivery_minutes": round(avg.total_seconds() / 60) if avg else None,
    }


class Pages(PageNumberPagination):
    page_size = 50
    max_page_size = 200
    page_size_query_param = "size"


def paged(view, request, queryset, row):
    pages = Pages()
    page = pages.paginate_queryset(queryset, request, view=view)
    return pages.get_paginated_response([row(item) for item in page])
