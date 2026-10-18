"""
Platform operations for Wasel staff: today's numbers, live orders, stuck-order
alerts, captains on the map, stores and accounts. Staff sign in through the
admin (session), so every endpoint here needs an active staff account.
"""

from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from orders.models import CaptainLocation, Order, StuckOrderAlert
from vendors.models import Vendor

ACTIVE = [Order.Status.RECEIVED, Order.Status.PREPARING, Order.Status.READY, Order.Status.OUT_FOR_DELIVERY]


class StaffView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]


def _since(day):
    """Start of a local calendar day, as an aware datetime."""
    return timezone.make_aware(datetime.combine(day, time.min))


def _money(value):
    return int(value or 0)


def _figures(orders):
    """Order counts and money for a set of orders (cancelled ones earn nothing)."""
    earning = orders.exclude(status=Order.Status.CANCELLED)
    sums = earning.aggregate(
        sales=Sum("total_amount"),
        commission=Sum("commission_amount"),
        service_fees=Sum("service_fee"),
        delivery_fees=Sum("delivery_fee"),
    )
    delivered = orders.filter(status=Order.Status.DELIVERED, delivered_at__isnull=False)
    avg = delivered.aggregate(
        avg=Avg(ExpressionWrapper(F("delivered_at") - F("created_at"), output_field=DurationField()))
    )["avg"]
    return {
        "orders": orders.count(),
        "delivered": delivered.count(),
        "cancelled": orders.filter(status=Order.Status.CANCELLED).count(),
        "sales": _money(sums["sales"]),
        "commission": _money(sums["commission"]),
        "service_fees": _money(sums["service_fees"]),
        "delivery_fees": _money(sums["delivery_fees"]),
        "avg_delivery_minutes": round(avg.total_seconds() / 60) if avg else None,
    }


class OverviewView(StaffView):
    """GET: today and this month in numbers, plus what's happening right now."""

    def get(self, request):
        today = timezone.localdate()
        today_orders = Order.objects.filter(created_at__gte=_since(today))
        month_orders = Order.objects.filter(created_at__gte=_since(today.replace(day=1)))
        by_status = dict(
            Order.objects.filter(status__in=ACTIVE).values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        top = (
            today_orders.exclude(status=Order.Status.CANCELLED)
            .values("vendor_id", "vendor__name")
            .annotate(orders=Count("id"), sales=Sum("total_amount"))
            .order_by("-orders", "-sales")[:5]
        )
        return Response(
            {
                "today": _figures(today_orders),
                "month": _figures(month_orders),
                "live": {
                    "active_orders": sum(by_status.values()),
                    "open_alerts": StuckOrderAlert.objects.filter(resolved_at__isnull=True).count(),
                    "online_captains": CaptainLocation.objects.filter(is_online=True).count(),
                    "open_stores": Vendor.objects.filter(is_open=True).count(),
                    "stores": Vendor.objects.count(),
                },
                "by_status": {status: by_status.get(status, 0) for status in ACTIVE},
                "top_stores": [
                    {"id": row["vendor_id"], "name": row["vendor__name"], "orders": row["orders"], "sales": _money(row["sales"])}
                    for row in top
                ],
            }
        )


class OrdersView(StaffView):
    """GET: every order still in progress, oldest first, with any open alerts."""

    def get(self, request):
        now = timezone.now()
        orders = (
            Order.objects.filter(status__in=ACTIVE)
            .select_related("vendor", "customer", "captain")
            .prefetch_related("stuck_alerts")
            .order_by("created_at")
        )
        return Response(
            [
                {
                    "id": o.pk,
                    "status": o.status,
                    "store": o.vendor.name,
                    "customer": o.customer.name or o.customer.phone,
                    "captain": (o.captain.name or o.captain.phone) if o.captain else None,
                    "total": _money(o.total_amount),
                    "payment_type": o.payment_type,
                    "minutes": int((now - o.created_at).total_seconds() // 60),
                    "alerts": [a.reason for a in o.stuck_alerts.all() if a.resolved_at is None],
                }
                for o in orders
            ]
        )


class AlertsView(StaffView):
    """GET: open stuck-order alerts, newest first."""

    def get(self, request):
        alerts = StuckOrderAlert.objects.filter(resolved_at__isnull=True).select_related("order__vendor")
        return Response(
            [
                {
                    "id": a.pk,
                    "order": a.order_id,
                    "store": a.order.vendor.name,
                    "status": a.order.status,
                    "reason": a.reason,
                    "minutes": int((timezone.now() - a.created_at).total_seconds() // 60),
                }
                for a in alerts
            ]
        )


class ResolveAlertView(StaffView):
    """POST: staff dealt with it (called the store, reassigned, ...)."""

    def post(self, request, pk):
        alert = get_object_or_404(StuckOrderAlert, pk=pk, resolved_at__isnull=True)
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["resolved_at"])
        return Response({"id": alert.pk, "resolved": True})


class CaptainsView(StaffView):
    """GET: captains who shared a location in the last day, online first."""

    def get(self, request):
        now = timezone.now()
        busy = dict(
            Order.objects.filter(status__in=[Order.Status.READY, Order.Status.OUT_FOR_DELIVERY], captain__isnull=False)
            .values_list("captain_id", "id")
        )
        locations = (
            CaptainLocation.objects.filter(Q(is_online=True) | Q(updated_at__gte=now - timedelta(days=1)))
            .select_related("captain")
            .order_by("-is_online", "-updated_at")
        )
        return Response(
            [
                {
                    "id": loc.captain_id,
                    "name": loc.captain.name,
                    "phone": loc.captain.phone,
                    "online": loc.is_online,
                    "lat": loc.point.y if loc.point else None,
                    "lng": loc.point.x if loc.point else None,
                    "seconds_ago": int((now - loc.updated_at).total_seconds()),
                    "order": busy.get(loc.captain_id),
                }
                for loc in locations
            ]
        )


class StoresView(StaffView):
    """GET: every store with today's orders and sales."""

    def get(self, request):
        since = _since(timezone.localdate())
        today = Q(orders__created_at__gte=since) & ~Q(orders__status=Order.Status.CANCELLED)
        stores = (
            Vendor.objects.select_related("owner")
            .annotate(orders_today=Count("orders", filter=today), sales_today=Sum("orders__total_amount", filter=today))
            .order_by("-is_open", "name")
        )
        return Response(
            [
                {
                    "id": v.pk,
                    "name": v.name,
                    "type": v.type,
                    "cuisine": v.cuisine,
                    "is_open": v.is_open,
                    "commission_rate": str(v.commission_rate.normalize()),
                    "owner": v.owner.name or v.owner.phone,
                    "orders_today": v.orders_today,
                    "sales_today": _money(v.sales_today),
                }
                for v in stores
            ]
        )


class OpenSerializer(serializers.Serializer):
    is_open = serializers.BooleanField()


class StoreOpenView(StaffView):
    """POST {is_open}: open or close a store for new orders (e.g. the owner called in)."""

    def post(self, request, pk):
        store = get_object_or_404(Vendor, pk=pk)
        data = OpenSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        store.is_open = data.validated_data["is_open"]
        store.save(update_fields=["is_open"])
        return Response({"id": store.pk, "is_open": store.is_open})


class UsersView(StaffView):
    """GET ?role=&q=: accounts, newest first (50 at a time), searchable by phone or name."""

    def get(self, request):
        users = User.objects.annotate(order_count=Count("orders")).order_by("-date_joined")
        role = request.query_params.get("role")
        if role in User.Role.values:
            users = users.filter(role=role)
        query = (request.query_params.get("q") or "").strip()
        if query:
            users = users.filter(Q(phone__icontains=query.lstrip("0")) | Q(name__icontains=query))
        counts = dict(User.objects.values_list("role").annotate(n=Count("id")).values_list("role", "n"))
        return Response(
            {
                "counts": {r: counts.get(r, 0) for r in User.Role.values},
                "results": [
                    {
                        "id": u.pk,
                        "phone": u.phone,
                        "name": u.name,
                        "role": u.role,
                        "is_active": u.is_active,
                        "is_staff": u.is_staff,
                        "orders": u.order_count,
                        "joined": u.date_joined.isoformat(),
                    }
                    for u in users[:50]
                ],
            }
        )


class ActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class UserActiveView(StaffView):
    """POST {is_active}: block or unblock an app account. Staff accounts are managed in the admin."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.is_staff or user.is_superuser:
            return Response(
                {"error": "staff_account", "detail": "Staff accounts are managed in the admin."}, status=400
            )
        data = ActiveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user.is_active = data.validated_data["is_active"]
        user.save(update_fields=["is_active"])
        return Response({"id": user.pk, "is_active": user.is_active})
