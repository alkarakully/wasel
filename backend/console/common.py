from datetime import datetime, time

from django.db.models import Avg, DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from orders.models import Order

ACTIVE = [Order.Status.RECEIVED, Order.Status.PREPARING, Order.Status.READY, Order.Status.OUT_FOR_DELIVERY]


def start_of(day):
    """Start of a local calendar day, as an aware datetime."""
    return timezone.make_aware(datetime.combine(day, time.min))


def money(value):
    return int(value or 0)


def iso(value):
    return value.isoformat() if value else None


def person(user):
    return {"id": user.pk, "name": user.name, "phone": user.phone} if user else None


def figures(orders):
    """Order counts and money for a set of orders (cancelled ones earn nothing)."""
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
        "sales": money(sums["sales"]),
        "commission": money(sums["commission"]),
        "service_fees": money(sums["service_fees"]),
        "delivery_fees": money(sums["delivery_fees"]),
        "discounts": money(sums["discounts"]),
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
