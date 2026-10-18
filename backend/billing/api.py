"""
Billing for store owners, and payouts for Wasel staff.

  GET  /api/vendors/{id}/billing/                  owner: this week so far, statements, totals
  GET  /api/vendors/{id}/statements/{sid}/         owner: one week with every order (?download=csv)
  GET  /api/ops/payouts/?status=due|paid           staff: statements across stores
  POST /api/ops/payouts/{sid}/paid/ {reference}    staff: mark a statement paid
  POST /api/ops/payouts/close/                     staff: make any missing statements now
"""

import csv
from datetime import timedelta

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from ops.api import StaffView
from vendors import access
from vendors.models import Vendor

from .models import Statement
from .weeks import close_finished_weeks, week_figures, week_orders, week_start


def _row(statement):
    return {
        "id": statement.pk,
        "store": statement.vendor_id,
        "store_name": statement.vendor.name,
        "period_start": statement.period_start.isoformat(),
        "period_end": statement.period_end.isoformat(),
        "orders_count": statement.orders_count,
        "food_sales": int(statement.food_sales),
        "store_discounts": int(statement.store_discounts),
        "commission": int(statement.commission),
        "payout": int(statement.payout),
        "status": statement.status,
        "paid_at": statement.paid_at.isoformat() if statement.paid_at else None,
        "paid_reference": statement.paid_reference,
    }


def _lines(vendor, start):
    """Every delivered order of the week, with what the store keeps from it."""
    orders = week_orders(vendor, start).select_related("offer").order_by("delivered_at")
    rows = []
    for o in orders:
        store_discount = int(o.discount) if o.offer_id and o.offer.vendor_id else 0
        rows.append(
            {
                "order": o.pk,
                "delivered_at": timezone.localtime(o.delivered_at).isoformat(),
                "payment_type": o.payment_type,
                "food_sales": int(o.subtotal),
                "store_discount": store_discount,
                "commission": int(o.commission_amount),
                "payout": int(o.subtotal) - store_discount - int(o.commission_amount),
            }
        )
    return rows


def _owner_store(request, pk):
    store = get_object_or_404(Vendor, pk=pk)
    return store if access.can(store, request.user, "billing") else None


DENIED = {"error": "not_allowed", "detail": "Only the store owner can see billing."}


class BillingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        store = _owner_store(request, pk)
        if store is None:
            return Response(DENIED, status=403)
        start = week_start(timezone.localdate())
        statements = Statement.objects.filter(vendor=store).select_related("vendor")
        totals = {
            status: int(statements.filter(status=status).aggregate(t=Sum("payout"))["t"] or 0)
            for status in Statement.Status.values
        }
        return Response(
            {
                "current_week": {
                    "period_start": start.isoformat(),
                    "period_end": (start + timedelta(days=6)).isoformat(),
                    **week_figures(store, start),
                },
                "due_total": totals[Statement.Status.DUE],
                "paid_total": totals[Statement.Status.PAID],
                "commission_rate": str(store.commission_rate.normalize()),
                "statements": [_row(s) for s in statements[:52]],
            }
        )


class StatementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, statement_id):
        store = _owner_store(request, pk)
        if store is None:
            return Response(DENIED, status=403)
        statement = get_object_or_404(Statement.objects.select_related("vendor"), pk=statement_id, vendor=store)
        lines = _lines(store, statement.period_start)
        if request.query_params.get("download") == "csv":
            return _csv(statement, lines)
        return Response({**_row(statement), "orders": lines})


def _csv(statement, lines):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    name = f"wasel-statement-{statement.vendor_id}-{statement.period_start:%Y-%m-%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    response.write("﻿")  # so Excel reads Arabic store names correctly
    writer = csv.writer(response)
    writer.writerow(["Store", statement.vendor.name])
    writer.writerow(["Week", f"{statement.period_start} to {statement.period_end}"])
    writer.writerow([])
    writer.writerow(["Order", "Delivered", "Payment", "Food sales (IQD)", "Store discount", "Wasel commission", "Payout"])
    for line in lines:
        writer.writerow(
            [line["order"], line["delivered_at"], line["payment_type"], line["food_sales"], line["store_discount"],
             line["commission"], line["payout"]]
        )
    writer.writerow([])
    writer.writerow(["Total", "", "", int(statement.food_sales), int(statement.store_discounts),
                     int(statement.commission), int(statement.payout)])
    writer.writerow(["Status", statement.get_status_display(), statement.paid_reference])
    return response


# --- Wasel staff ---------------------------------------------------------------------


class PayoutsView(StaffView):
    def get(self, request):
        statements = Statement.objects.select_related("vendor")
        if (status := request.query_params.get("status")) in Statement.Status.values:
            statements = statements.filter(status=status)
        due = Statement.objects.filter(status=Statement.Status.DUE).aggregate(t=Sum("payout"))["t"]
        return Response({"due_total": int(due or 0), "results": [_row(s) for s in statements[:200]]})


class PaidSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100, allow_blank=True, required=False, default="")


class MarkPaidView(StaffView):
    def post(self, request, pk):
        statement = get_object_or_404(Statement.objects.select_related("vendor"), pk=pk)
        if statement.status == Statement.Status.PAID:
            return Response({"error": "already_paid", "detail": "This statement is already paid."}, status=400)
        data = PaidSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        statement.status = Statement.Status.PAID
        statement.paid_at = timezone.now()
        statement.paid_reference = data.validated_data["reference"]
        statement.paid_by = request.user
        statement.save(update_fields=["status", "paid_at", "paid_reference", "paid_by"])
        return Response(_row(statement))


class CloseWeeksView(StaffView):
    def post(self, request):
        return Response({"made": len(close_finished_weeks())})
