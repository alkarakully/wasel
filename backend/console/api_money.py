"""Store payouts, wallet movements, platform reports, offers and Wasel Plus."""

from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from accounts.models import WalletTransaction
from billing.api import _row as statement_row
from billing.models import Statement
from billing.weeks import close_finished_weeks
from orders.models import Order
from regions.regions import quantize, region
from regions.serializers import check_amount
from subscriptions.models import WaselPlusSubscription
from vendors.models import Offer, Vendor

from .access import ConsoleView
from .audit import diff, record
from .common import country_param, figures, iso, local_today, money, paged, person, start_of

# --- Payouts ------------------------------------------------------------------------


class PayoutsView(ConsoleView):
    """GET ?country=&status=due|paid&store=&page=: one country's weekly store statements."""

    area = "money"

    def get(self, request):
        p = request.query_params
        country = country_param(request)
        currency = region(country).currency
        statements = Statement.objects.select_related("vendor").filter(vendor__country=country)
        if p.get("status") in Statement.Status.values:
            statements = statements.filter(status=p["status"])
        if (store := p.get("store", "")).isdigit():
            statements = statements.filter(vendor_id=store)
        due = Statement.objects.filter(status=Statement.Status.DUE, vendor__country=country).aggregate(
            t=Sum("payout"), n=Count("id")
        )
        response = paged(self, request, statements, statement_row)
        response.data["currency"] = currency
        response.data["due_total"] = money(due["t"], currency)
        response.data["due_count"] = due["n"]
        return response


class PaidInput(serializers.Serializer):
    reference = serializers.CharField(max_length=100, allow_blank=True, required=False, default="")


class PayoutPaidView(ConsoleView):
    """POST {reference}: the transfer went out."""

    area = "money"

    def post(self, request, pk):
        statement = get_object_or_404(Statement.objects.select_related("vendor"), pk=pk)
        if statement.status == Statement.Status.PAID:
            return Response({"error": "already_paid", "detail": "This statement is already paid."}, status=400)
        data = PaidInput(data=request.data)
        data.is_valid(raise_exception=True)
        statement.status = Statement.Status.PAID
        statement.paid_at = timezone.now()
        statement.paid_reference = data.validated_data["reference"]
        statement.paid_by = request.user
        statement.save(update_fields=["status", "paid_at", "paid_reference", "paid_by"])
        record(
            request,
            "payout.paid",
            f"Paid {statement.vendor.name} {money(statement.payout, statement.currency)} {statement.currency}"
            f" for the week of {statement.period_start}",
            statement,
            {"reference": statement.paid_reference},
        )
        return Response(statement_row(statement))


class CloseWeeksView(ConsoleView):
    area = "money"

    def post(self, request):
        made = len(close_finished_weeks())
        record(request, "payout.close_weeks", f"Closed finished weeks ({made} new statements)")
        return Response({"made": made})


# --- Wallet ----------------------------------------------------------------------


class WalletView(ConsoleView):
    """GET ?country=&type=&q=&page=: wallet movements in one country's currency, newest first."""

    area = "money"

    def get(self, request):
        p = request.query_params
        currency = region(country_param(request)).currency
        entries = WalletTransaction.objects.select_related("user").filter(currency=currency)
        if p.get("type") in WalletTransaction.Type.values:
            entries = entries.filter(type=p["type"])
        if q := p.get("q", "").strip():
            entries = entries.filter(Q(user__phone__icontains=q.lstrip("0")) | Q(user__name__icontains=q))
        totals = dict(
            WalletTransaction.objects.filter(currency=currency)
            .values_list("type")
            .annotate(t=Sum("amount"))
            .values_list("type", "t")
        )
        response = paged(
            self,
            request,
            entries,
            lambda t: {
                "id": t.pk,
                "user": person(t.user),
                "type": t.type,
                "currency": t.currency,
                "amount": money(t.amount, t.currency),
                "order": t.order_id,
                "created_at": t.created_at.isoformat(),
            },
        )
        response.data["currency"] = currency
        response.data["totals"] = {k: money(totals.get(k), currency) for k in WalletTransaction.Type.values}
        return response


# --- Reports ---------------------------------------------------------------------


def _day(value, fallback):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


class ReportsView(ConsoleView):
    """GET ?country=&from=YYYY-MM-DD&to=YYYY-MM-DD (to included, at most a year): one country's numbers."""

    area = "reports"

    def get(self, request):
        country = country_param(request)
        r = region(country)
        today = local_today(country)
        end = _day(request.query_params.get("to"), today)
        start = _day(request.query_params.get("from"), end - timedelta(days=29))
        if start > end:
            start, end = end, start
        start = max(start, end - timedelta(days=365))
        orders = Order.objects.filter(
            vendor__country=country,
            created_at__gte=start_of(start, country),
            created_at__lt=start_of(end + timedelta(days=1), country),
        )
        earning = orders.exclude(status=Order.Status.CANCELLED)
        daily = {
            row["day"]: row
            for row in earning.annotate(day=TruncDate("created_at", tzinfo=r.tz))
            .values("day")
            .annotate(orders=Count("id"), sales=Sum("total_amount"), commission=Sum("commission_amount"))
        }
        stores = (
            earning.values("vendor_id", "vendor__name")
            .annotate(orders=Count("id"), sales=Sum("total_amount"), commission=Sum("commission_amount"))
            .order_by("-sales")[:50]
        )
        payments = earning.values("payment_type").annotate(orders=Count("id"), sales=Sum("total_amount"))
        cancelled = orders.filter(status=Order.Status.CANCELLED).values("cancelled_by").annotate(n=Count("id"))
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        return Response(
            {
                "from": start.isoformat(),
                "to": end.isoformat(),
                "country": country,
                "currency": r.currency,
                "time_zone": r.time_zone,
                "totals": figures(orders, r.currency),
                "customers": orders.values("customer_id").distinct().count(),
                "days": [
                    {
                        "day": d.isoformat(),
                        "orders": daily.get(d, {}).get("orders", 0),
                        "sales": money(daily.get(d, {}).get("sales"), r.currency),
                        "commission": money(daily.get(d, {}).get("commission"), r.currency),
                    }
                    for d in days
                ],
                "stores": [
                    {
                        "id": row["vendor_id"],
                        "name": row["vendor__name"],
                        "orders": row["orders"],
                        "sales": money(row["sales"], r.currency),
                        "commission": money(row["commission"], r.currency),
                    }
                    for row in stores
                ],
                "payments": {
                    row["payment_type"]: {"orders": row["orders"], "sales": money(row["sales"], r.currency)}
                    for row in payments
                },
                "cancelled_by": {row["cancelled_by"] or "unknown": row["n"] for row in cancelled},
            }
        )


# --- Offers and banners ---------------------------------------------------------------


class OfferInput(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ["vendor", "country", "title", "type", "value", "min_order", "starts_at", "ends_at", "is_banner"]
        extra_kwargs = {"vendor": {"required": False, "allow_null": True}, "country": {"required": False}}

    def validate(self, data):
        # A store's offer is in its store's country and currency; a platform-wide one names its country.
        vendor = data.get("vendor", getattr(self.instance, "vendor", None))
        country = vendor.country if vendor else data.get("country", getattr(self.instance, "country", "IQ"))
        data["country"] = country
        currency = region(country).currency
        starts = data.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = data.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts and ends and ends <= starts:
            raise serializers.ValidationError({"ends_at": "End after it starts."})
        kind = data.get("type", getattr(self.instance, "type", None))
        value = data.get("value", getattr(self.instance, "value", 0))
        if kind == Offer.Type.PERCENT and not (0 < value <= 100):
            raise serializers.ValidationError({"value": "A percentage from 1 to 100."})
        if kind == Offer.Type.FIXED and value <= 0:
            raise serializers.ValidationError({"value": "Enter an amount above zero."})
        try:
            if kind == Offer.Type.FIXED:
                check_amount(value, currency)
            check_amount(data.get("min_order", getattr(self.instance, "min_order", 0)), currency)
        except serializers.ValidationError as error:
            field = "value" if kind == Offer.Type.FIXED and value != quantize(value, currency) else "min_order"
            raise serializers.ValidationError({field: error.detail}) from error
        return data


def offer_row(o, now=None):
    now = now or timezone.now()
    state = "scheduled" if o.starts_at > now else "ended" if o.ends_at <= now else "running"
    return {
        "id": o.pk,
        "store": {"id": o.vendor_id, "name": o.vendor.name} if o.vendor_id else None,
        "title": o.title,
        "type": o.type,
        "country": o.country,
        "currency": o.currency,
        "value": money(o.value, o.currency) if o.type == Offer.Type.FIXED else f"{o.value.normalize():f}",
        "min_order": money(o.min_order, o.currency),
        "starts_at": o.starts_at.isoformat(),
        "ends_at": o.ends_at.isoformat(),
        "is_banner": o.is_banner,
        "state": state,
        "orders": getattr(o, "order_count", None),
    }


class OffersView(ConsoleView):
    """GET ?state=running|scheduled|ended&scope=platform|store: offers. POST: a new one."""

    area = "marketing"

    def get(self, request):
        p, now = request.query_params, timezone.now()
        offers = Offer.objects.select_related("vendor").annotate(order_count=Count("orders"))
        state = p.get("state")
        if state == "running":
            offers = offers.filter(starts_at__lte=now, ends_at__gt=now)
        elif state == "scheduled":
            offers = offers.filter(starts_at__gt=now)
        elif state == "ended":
            offers = offers.filter(ends_at__lte=now)
        if p.get("country"):
            offers = offers.filter(country=country_param(request))
        if p.get("scope") == "platform":
            offers = offers.filter(vendor__isnull=True)
        elif p.get("scope") == "store":
            offers = offers.filter(vendor__isnull=False)
        return paged(self, request, offers, lambda o: offer_row(o, now))

    def post(self, request):
        data = OfferInput(data=request.data)
        data.is_valid(raise_exception=True)
        offer = data.save()
        record(request, "offer.create", f"Created offer {offer.title}", offer)
        return Response(offer_row(offer), status=201)


class OfferView(ConsoleView):
    area = "marketing"

    def patch(self, request, pk):
        offer = get_object_or_404(Offer.objects.select_related("vendor"), pk=pk)
        data = OfferInput(offer, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        changes = diff(offer, data.validated_data, OfferInput.Meta.fields)
        offer = data.save()
        if changes:
            record(request, "offer.update", f"Edited offer {offer.title}", offer, changes)
        return Response(offer_row(offer))

    def delete(self, request, pk):
        """An offer nobody used is deleted; a used one ends now, so old orders keep it."""
        offer = get_object_or_404(Offer, pk=pk)
        if offer.orders.exists():
            offer.ends_at = min(offer.ends_at, timezone.now())
            offer.save(update_fields=["ends_at"])
            record(request, "offer.end", f"Ended offer {offer.title}", offer)
        else:
            record(request, "offer.delete", f"Deleted offer {offer.title}", offer)
            offer.delete()
        return Response(status=204)


# --- Wasel Plus ------------------------------------------------------------------


class PlusView(ConsoleView):
    """GET ?status=&q=&page=: Wasel Plus members."""

    area = "marketing"

    def get(self, request):
        p = request.query_params
        subs = WaselPlusSubscription.objects.select_related("user")
        if p.get("status") in WaselPlusSubscription.Status.values:
            subs = subs.filter(status=p["status"])
        if q := p.get("q", "").strip():
            subs = subs.filter(Q(user__phone__icontains=q.lstrip("0")) | Q(user__name__icontains=q))
        counts = dict(
            WaselPlusSubscription.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        response = paged(
            self,
            request,
            subs,
            lambda s: {
                "id": s.pk,
                "user": person(s.user),
                "status": s.status,
                "trial_end": iso(s.trial_end_date),
                "renews_at": iso(s.renews_at),
                "created_at": s.created_at.isoformat(),
            },
        )
        response.data["counts"] = {k: counts.get(k, 0) for k in WaselPlusSubscription.Status.values}
        return response


class StoreChoicesView(ConsoleView):
    """GET: approved stores as {id, name}, for pickers (offers, filters)."""

    area = None

    def get(self, request):
        stores = Vendor.objects.filter(status=Vendor.Status.APPROVED).order_by("name")
        if request.query_params.get("country"):
            stores = stores.filter(country=country_param(request))
        return Response(list(stores.values("id", "name", "country")))
