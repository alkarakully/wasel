"""Overview, orders, dispatch, stuck-order alerts and captains on the map."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from accounts.models import User
from orders import dispatch, realtime, workflow
from orders.models import CaptainLocation, Order, StuckOrderAlert
from subscriptions.models import WaselPlusSubscription
from regions.regions import region
from vendors.models import Vendor

from .access import ConsoleView
from .audit import record
from .common import ACTIVE, country_param, figures, iso, local_today, money, paged, person, start_of


class OverviewView(ConsoleView):
    """GET: today and this month in numbers, what's live now, and the last 14 days."""

    area = "overview"

    def get(self, request):
        country = country_param(request)
        r = region(country)
        here = Order.objects.filter(vendor__country=country)
        stores = Vendor.objects.filter(country=country)
        today = local_today(country)
        today_orders = here.filter(created_at__gte=start_of(today, country))
        month_orders = here.filter(created_at__gte=start_of(today.replace(day=1), country))
        by_status = dict(
            here.filter(status__in=ACTIVE).values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        top = (
            today_orders.exclude(status=Order.Status.CANCELLED)
            .values("vendor_id", "vendor__name")
            .annotate(orders=Count("id"), sales=Sum("total_amount"))
            .order_by("-orders", "-sales")[:5]
        )
        first = today - timedelta(days=13)
        daily = {
            row["day"]: row
            for row in here.filter(created_at__gte=start_of(first, country))
            .exclude(status=Order.Status.CANCELLED)
            .annotate(day=TruncDate("created_at", tzinfo=r.tz))
            .values("day")
            .annotate(orders=Count("id"), sales=Sum("total_amount"))
        }
        days = [first + timedelta(days=i) for i in range(14)]
        return Response(
            {
                "country": country,
                "currency": r.currency,
                "time_zone": r.time_zone,
                "today": figures(today_orders, r.currency),
                "month": figures(month_orders, r.currency),
                "live": {
                    "active_orders": sum(by_status.values()),
                    "open_alerts": StuckOrderAlert.objects.filter(
                        resolved_at__isnull=True, order__vendor__country=country
                    ).count(),
                    # Captains aren't tied to a country; the map shows where they are.
                    "online_captains": CaptainLocation.objects.filter(is_online=True).count(),
                    "open_stores": stores.filter(status=Vendor.Status.APPROVED, is_open=True).count(),
                    "stores": stores.filter(status=Vendor.Status.APPROVED).count(),
                    "applications": stores.filter(status=Vendor.Status.PENDING).count(),
                    "customers": User.objects.filter(role=User.Role.CUSTOMER, country=country).count(),
                    "plus_members": WaselPlusSubscription.objects.filter(user__country=country)
                    .exclude(status=WaselPlusSubscription.Status.EXPIRED)
                    .count(),
                },
                "by_status": {s: by_status.get(s, 0) for s in ACTIVE},
                "days": [
                    {
                        "day": d.isoformat(),
                        "orders": daily.get(d, {}).get("orders", 0),
                        "sales": money(daily.get(d, {}).get("sales"), r.currency),
                    }
                    for d in days
                ],
                "top_stores": [
                    {"id": t["vendor_id"], "name": t["vendor__name"], "orders": t["orders"], "sales": money(t["sales"], r.currency)}
                    for t in top
                ],
            }
        )


def order_row(o, now=None):
    now = now or timezone.now()
    return {
        "id": o.pk,
        "status": o.status,
        "store": {"id": o.vendor_id, "name": o.vendor.name},
        "customer": person(o.customer),
        "captain": person(o.captain),
        "currency": o.currency,
        "total": money(o.total_amount, o.currency),
        "payment_type": o.payment_type,
        "payment_status": o.payment_status,
        "created_at": o.created_at.isoformat(),
        "minutes": int((now - o.created_at).total_seconds() // 60),
        "alerts": [a.reason for a in o.stuck_alerts.all() if a.resolved_at is None],
    }


class OrdersView(ConsoleView):
    """GET ?scope=live|all&status=&store=&q=&page=: orders, live ones oldest first."""

    area = "orders"

    def get(self, request):
        p = request.query_params
        orders = Order.objects.select_related("vendor", "customer", "captain").prefetch_related("stuck_alerts")
        live = p.get("scope", "live") == "live"
        if live:
            orders = orders.filter(status__in=ACTIVE).order_by("created_at")
        else:
            orders = orders.order_by("-created_at")
        if p.get("status") in Order.Status.values:
            orders = orders.filter(status=p["status"])
        if p.get("country"):
            orders = orders.filter(vendor__country=country_param(request))
        if (store := p.get("store", "")).isdigit():
            orders = orders.filter(vendor_id=store)
        if (customer := p.get("customer", "")).isdigit():
            orders = orders.filter(customer_id=customer)
        if (captain := p.get("captain", "")).isdigit():
            orders = orders.filter(captain_id=captain)
        if q := p.get("q", "").strip().lstrip("#"):
            if q.isdigit() and len(q) < 7:
                # Short numbers are order numbers, longer ones phone numbers.
                orders = orders.filter(pk=int(q))
            else:
                orders = orders.filter(
                    Q(customer__phone__icontains=q.lstrip("0")) | Q(customer__name__icontains=q) | Q(vendor__name__icontains=q)
                )
        now = timezone.now()
        return paged(self, request, orders, lambda o: order_row(o, now))


def order_detail(o):
    timeline = [
        (step, at)
        for step, at in [
            ("received", o.created_at),
            ("accepted", o.accepted_at),
            ("ready", o.ready_at),
            ("picked_up", o.picked_up_at),
            ("delivered", o.delivered_at),
            ("cancelled", o.cancelled_at),
        ]
        if at
    ]
    return {
        **order_row(o),
        "store": {"id": o.vendor_id, "name": o.vendor.name, "phone": o.vendor.owner.phone},
        "delivery_address": o.delivery_address,
        "delivery": {"lat": o.delivery_location.y, "lng": o.delivery_location.x},
        "store_location": {"lat": o.vendor.location.y, "lng": o.vendor.location.x},
        "subtotal": money(o.subtotal, o.currency),
        "delivery_fee": money(o.delivery_fee, o.currency),
        "service_fee": money(o.service_fee, o.currency),
        "tip": money(o.tip, o.currency),
        "discount": money(o.discount, o.currency),
        # The part of the discount the store pays (its deals and offers); the rest is Wasel's.
        "store_discount": money(o.store_discount, o.currency),
        "commission": money(o.commission_amount, o.currency),
        "time_zone": o.vendor.region.time_zone,
        "estimated_ready_at": iso(o.estimated_ready_at),
        "cancelled_by": o.cancelled_by,
        "cancel_reason": o.cancel_reason,
        "timeline": [{"step": step, "at": at.isoformat()} for step, at in sorted(timeline, key=lambda t: t[1])],
        "items": [
            {
                "name": i.product.name_ar,
                "name_en": i.product.name_en,
                "quantity": str(i.quantity.normalize()),
                "price": money(i.unit_price, o.currency),
                "options": [m.modifier.name_ar for m in i.modifiers.all()],
            }
            for i in o.items.all()
        ],
        "alerts": [
            {"id": a.pk, "reason": a.reason, "created_at": a.created_at.isoformat(), "resolved_at": iso(a.resolved_at)}
            for a in o.stuck_alerts.all()
        ],
        "offers": [
            {
                "captain": person(d.captain),
                "status": d.status,
                "distance_m": round(d.distance_m),
                "created_at": d.created_at.isoformat(),
            }
            for d in o.dispatch_offers.select_related("captain").order_by("created_at")
        ],
        "can_cancel": o.status not in (Order.Status.DELIVERED, Order.Status.CANCELLED),
        "can_release": o.captain_id is not None and o.status in (Order.Status.PREPARING, Order.Status.READY),
        "can_dispatch": o.waiting_for_captain,
    }


def _load(pk):
    return get_object_or_404(
        Order.objects.select_related("vendor__owner", "customer", "captain").prefetch_related(
            "stuck_alerts", "items__product", "items__modifiers__modifier"
        ),
        pk=pk,
    )


class OrderView(ConsoleView):
    area = "orders"

    def get(self, request, pk):
        return Response(order_detail(_load(pk)))


class ReasonInput(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Say why.")
        return value.strip()


def _resolve_alerts(order_id):
    StuckOrderAlert.objects.filter(order_id=order_id, resolved_at__isnull=True).update(resolved_at=timezone.now())


class CancelOrderView(ConsoleView):
    """POST {reason}: Wasel support cancels the order. A wallet payment goes back to the wallet."""

    area = "orders"

    def post(self, request, pk):
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        reason = data.validated_data["reason"]
        with transaction.atomic():
            order = workflow._lock(pk)
            if order.status in (Order.Status.DELIVERED, Order.Status.CANCELLED):
                return Response({"error": "invalid_transition", "detail": f"Order #{order.pk} is {order.status}."}, status=409)
            was_available = order.in_open_pool()
            workflow._cancel(order, Order.CancelledBy.SUPPORT, reason)
            dispatch.withdraw(order.pk, "cancelled")
            _resolve_alerts(order.pk)
            realtime.broadcast_order(order.pk, was_available)
            record(request, "order.cancel", f"Cancelled order #{order.pk}", order, {"reason": reason, "refunded": order.payment_status == Order.PaymentStatus.REFUNDED})
        return Response(order_detail(_load(pk)))


class ReleaseCaptainView(ConsoleView):
    """POST {reason}: take the order off a captain who can't make it and offer it to the next one."""

    area = "orders"

    def post(self, request, pk):
        data = ReasonInput(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            order = workflow._lock(pk)
            if order.captain_id is None or order.status not in (Order.Status.PREPARING, Order.Status.READY):
                return Response(
                    {"error": "invalid_transition", "detail": "Only a captain who hasn't picked up yet can be released."},
                    status=409,
                )
            captain_id = order.captain_id
            order.captain = None
            order.save(update_fields=["captain", "updated_at"])
            # The broadcast no longer reaches them, so tell the old captain directly.
            transaction.on_commit(lambda: _tell_released(captain_id, order.pk))
            dispatch.offer_next(order.pk, announce_if_none=False)
            realtime.broadcast_order(order.pk, False)
            record(request, "order.release", f"Released the captain from order #{order.pk}", order,
                   {"captain": captain_id, "reason": data.validated_data["reason"]})
        return Response(order_detail(_load(pk)))


def _tell_released(captain_id, order_id):
    order = Order.objects.select_related("vendor").get(pk=order_id)
    realtime.notify_user(captain_id, {"type": "order.updated", "order": realtime._order_data(order)})


class DispatchView(ConsoleView):
    """POST: offer a waiting order to the nearest free captain now."""

    area = "orders"

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if not order.waiting_for_captain:
            return Response({"error": "invalid_transition", "detail": "This order isn't waiting for a captain."}, status=409)
        was_available = order.in_open_pool()
        offer = dispatch.offer_next(order.pk, announce_if_none=False)
        realtime.broadcast_order(order.pk, was_available)
        record(request, "order.dispatch", f"Sent order #{order.pk} to dispatch", order)
        return Response({**order_detail(_load(pk)), "offered": offer is not None})


class AlertsView(ConsoleView):
    """GET: open stuck-order alerts, newest first."""

    area = "orders"

    def get(self, request):
        now = timezone.now()
        alerts = StuckOrderAlert.objects.filter(resolved_at__isnull=True).select_related("order__vendor")
        if request.query_params.get("country"):
            alerts = alerts.filter(order__vendor__country=country_param(request))
        return Response(
            [
                {
                    "id": a.pk,
                    "order": a.order_id,
                    "store": a.order.vendor.name,
                    "status": a.order.status,
                    "reason": a.reason,
                    "minutes": int((now - a.created_at).total_seconds() // 60),
                }
                for a in alerts
            ]
        )


class ResolveAlertView(ConsoleView):
    area = "orders"

    def post(self, request, pk):
        alert = get_object_or_404(StuckOrderAlert, pk=pk, resolved_at__isnull=True)
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["resolved_at"])
        record(request, "alert.resolve", f"Resolved {alert.reason} alert on order #{alert.order_id}", alert)
        return Response({"id": alert.pk, "resolved": True})


class CaptainsMapView(ConsoleView):
    """GET: captains who shared a location in the last day, online first, with the order they carry."""

    area = "orders"

    def get(self, request):
        now = timezone.now()
        busy = dict(
            Order.objects.filter(status__in=[Order.Status.PREPARING, Order.Status.READY, Order.Status.OUT_FOR_DELIVERY], captain__isnull=False)
            .values_list("captain_id", "id")
        )
        locations = (
            CaptainLocation.objects.filter(Q(is_online=True) | Q(updated_at__gte=now - timedelta(days=1)))
            .select_related("captain")
            .order_by("-is_online", "-updated_at")
        )
        stores = Vendor.objects.filter(status=Vendor.Status.APPROVED)
        if request.query_params.get("country"):
            stores = stores.filter(country=country_param(request))
        return Response(
            {
                "captains": [
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
                ],
                "stores": [
                    {"id": s.pk, "name": s.name, "open": s.is_open, "lat": s.location.y, "lng": s.location.x}
                    for s in stores
                ],
            }
        )
