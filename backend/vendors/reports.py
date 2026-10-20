"""
GET /api/vendors/{id}/report/?from=YYYY-MM-DD&to=YYYY-MM-DD

A store's numbers for a date range (calendar days where the store is, both ends included;
the last 7 days by default): sales, orders, what they earned after Wasel's
commission, a day-by-day series, top items, busiest hours, prep times and
cancellations. For the owner and managers.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from regions.regions import as_api

from . import access
from .models import Vendor

MAX_DAYS = 366


def _day(value, default):
    try:
        return date.fromisoformat(value) if value else default
    except ValueError:
        return None


def _money(value):
    return Decimal(value or 0)


def store_payout(orders):
    """Food sales, store-funded discounts, commission and what the store keeps (Decimals, in the store's currency)."""
    sums = orders.aggregate(
        food=Sum("subtotal"),
        commission=Sum("commission_amount"),
        # Recorded at checkout: the store's item deals and its own offers; Wasel pays for its own.
        store_discounts=Sum("store_discount"),
    )
    food, commission, discounts = _money(sums["food"]), _money(sums["commission"]), _money(sums["store_discounts"])
    return {
        "food_sales": food,
        "store_discounts": discounts,
        "commission": commission,
        "payout": food - discounts - commission,
    }


class ReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        store = get_object_or_404(Vendor, pk=pk)
        if not access.can(store, request.user, "reports"):
            return Response({"error": "not_allowed", "detail": "Only the owner or a manager can see reports."}, status=403)

        tz = store.tz
        today = timezone.localdate(timezone=tz)
        end = _day(request.query_params.get("to"), today)
        start = _day(request.query_params.get("from"), (end or today) - timedelta(days=6))
        if start is None or end is None or start > end or (end - start).days >= MAX_DAYS:
            return Response(
                {"error": "invalid_range", "detail": "Pick a start on or before the end, at most a year apart."},
                status=400,
            )

        since = timezone.make_aware(datetime.combine(start, time.min), tz)
        until = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
        orders = Order.objects.filter(vendor=store, created_at__gte=since, created_at__lt=until)
        delivered = orders.filter(status=Order.Status.DELIVERED)
        cancelled = orders.filter(status=Order.Status.CANCELLED)

        currency = store.currency

        def fmt(amount):
            return as_api(amount, currency)

        money = store_payout(delivered)
        delivered_count = delivered.count()
        prep = orders.filter(accepted_at__isnull=False, ready_at__isnull=False).aggregate(
            avg=Avg(ExpressionWrapper(F("ready_at") - F("accepted_at"), output_field=DurationField()))
        )["avg"]

        by_day = {
            row["day"]: row
            for row in delivered.annotate(day=TruncDate("created_at", tzinfo=tz))
            .values("day")
            .annotate(orders=Count("id"), sales=Sum("subtotal"))
        }
        days = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            row = by_day.get(day, {})
            days.append({"date": day.isoformat(), "orders": row.get("orders", 0), "sales": fmt(_money(row.get("sales")))})

        hours = dict(
            orders.exclude(status=Order.Status.CANCELLED)
            .annotate(hour=ExtractHour("created_at", tzinfo=tz))
            .values_list("hour")
            .annotate(n=Count("id"))
            .values_list("hour", "n")
        )

        top = (
            OrderItem.objects.filter(order__in=delivered)
            .values("product_id", "product__name_ar", "product__name_ku", "product__name_en")
            .annotate(quantity=Sum("quantity"), sales=Sum("line_total"), orders=Count("order", distinct=True))
            .order_by("-sales")[:10]
        )

        return Response(
            {
                "from": start.isoformat(),
                "to": end.isoformat(),
                "currency": currency,
                "orders": orders.count(),
                "delivered": delivered_count,
                "cancelled": cancelled.count(),
                "cancelled_by": dict(cancelled.values_list("cancelled_by").annotate(n=Count("id")).values_list("cancelled_by", "n")),
                **{key: fmt(value) for key, value in money.items()},
                "average_order": fmt(money["food_sales"] / delivered_count if delivered_count else 0),
                "average_prep_minutes": round(prep.total_seconds() / 60) if prep else None,
                "days": days,
                "hours": [{"hour": h, "orders": hours.get(h, 0)} for h in range(24)],
                "top_items": [
                    {
                        "product": row["product_id"],
                        "name": {"ar": row["product__name_ar"], "ku": row["product__name_ku"], "en": row["product__name_en"]},
                        "quantity": str(row["quantity"].normalize()) if row["quantity"] is not None else "0",
                        "orders": row["orders"],
                        "sales": fmt(_money(row["sales"])),
                    }
                    for row in top
                ],
            }
        )
