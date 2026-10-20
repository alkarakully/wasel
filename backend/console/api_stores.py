"""Stores, their applications, menus and teams, as Wasel staff see them."""

from decimal import Decimal

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from accounts.models import User
from accounts.phone import InvalidPhone, normalize_phone
from accounts.serializers import CountryField
from orders.models import Order
from regions.serializers import check_amount
from regions.regions import CODES as REGION_CODES
from regions.regions import region as region_for
from regions.regions import where
from vendors.models import Product, StoreMember, Vendor
from vendors.onboarding import make_store_account, store_account_problem

from .access import ConsoleView
from .audit import diff, record
from .common import country_param, local_today, money, start_of

def store_row(v, orders_today=None, sales_today=None):
    row = {
        "id": v.pk,
        "name": v.name,
        "type": v.type,
        "cuisine": v.cuisine,
        "is_open": v.is_open,
        "status": v.status,
        "country": v.country,
        "currency": v.currency,
        "owner": {"id": v.owner_id, "phone": v.owner.phone, "name": v.owner.name},
        "commission_rate": str(v.commission_rate.normalize()),
        "created_at": v.created_at.isoformat(),
    }
    if orders_today is not None:
        row["orders_today"] = orders_today
        row["sales_today"] = money(sales_today, v.currency)
    return row


def store_detail(v):
    return {
        **store_row(v),
        "address": v.address,
        "latitude": v.location.y,
        "longitude": v.location.x,
        "delivery_radius_km": str(v.delivery_radius_km.normalize()),
        "commission_free_until": v.commission_free_until.isoformat() if v.commission_free_until else None,
        "opening_hours": v.opening_hours,
        "time_zone": v.region.time_zone,
        "rejection_reason": v.rejection_reason,
        "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
    }


def _owner_for(phone, name="", country="IQ"):
    """A store account for this phone: an existing one, a fresh customer account turned into one, or a new one."""
    try:
        phone = normalize_phone(phone, country)
    except InvalidPhone as error:
        raise serializers.ValidationError({"owner_phone": [str(error)]}) from error
    user = User.objects.filter(phone=phone).first()
    if user is None:
        return User.objects.create_user(phone, name=name, role=User.Role.VENDOR)
    if store_account_problem(user):
        raise serializers.ValidationError({"owner_phone": ["This number belongs to another kind of account."]})
    make_store_account(user, name)
    return user


class StoreInput(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    type = serializers.ChoiceField(choices=Vendor.Type.choices, required=False)
    cuisine = serializers.ChoiceField(choices=Vendor.Cuisine.choices, required=False, allow_blank=True)
    address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    delivery_radius_km = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=Decimal("0.5"), max_value=Decimal("50"))
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=Decimal("0"), max_value=Decimal("50"))
    commission_free_until = serializers.DateTimeField(required=False, allow_null=True)
    is_open = serializers.BooleanField(required=False)
    # Where the store trades (currency, clock, fees). Guessed from the map spot when left out.
    country = serializers.ChoiceField(choices=REGION_CODES, required=False)
    owner_phone = serializers.CharField(required=False)
    owner_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    # The owner phone's country; local numbers are read in it.
    owner_country = CountryField()


EDITABLE = [
    "name", "type", "cuisine", "address", "delivery_radius_km", "commission_rate", "commission_free_until", "is_open",
]


class StoresView(ConsoleView):
    """GET ?status=&q=: every store with today's numbers. POST: create a store (approved) with its owner."""

    area = "stores"

    def get(self, request):
        # One country at a time: "today" and the sales sums follow its clock and currency.
        country = country_param(request)
        since = start_of(local_today(country), country)
        today = Q(orders__created_at__gte=since) & ~Q(orders__status=Order.Status.CANCELLED)
        stores = Vendor.objects.filter(country=country).select_related("owner").annotate(
            orders_today=Count("orders", filter=today), sales_today=Sum("orders__total_amount", filter=today)
        )
        status = request.query_params.get("status")
        if status in Vendor.Status.values:
            stores = stores.filter(status=status)
        if q := (request.query_params.get("q") or "").strip():
            stores = stores.filter(Q(name__icontains=q) | Q(owner__phone__icontains=q.lstrip("0")) | Q(owner__name__icontains=q))
        counts = dict(
            Vendor.objects.filter(country=country).values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        return Response(
            {
                "counts": {st: counts.get(st, 0) for st in Vendor.Status.values},
                "results": [store_row(v, v.orders_today, v.sales_today) for v in stores.order_by("-created_at")[:300]],
            }
        )

    def post(self, request):
        data = StoreInput(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        missing = [f for f in ("name", "latitude", "longitude", "owner_phone") if f not in d]
        if missing:
            return Response({f: ["This field is required."] for f in missing}, status=400)
        country = d.get("country") or where(d["latitude"], d["longitude"])
        if country is None:
            return Response({"country": ["Wasel doesn't run stores in this area yet. Choose the country."]}, status=400)
        if not region_for(country).contains(d["latitude"], d["longitude"]):
            return Response({"latitude": [f"This spot isn't in {country}."]}, status=400)
        with transaction.atomic():
            owner = _owner_for(d["owner_phone"], d.get("owner_name", ""), d.get("owner_country", "IQ"))
            store = Vendor.objects.create(
                owner=owner,
                name=d["name"],
                type=d.get("type", Vendor.Type.RESTAURANT),
                cuisine=d.get("cuisine", ""),
                location=Point(d["longitude"], d["latitude"], srid=4326),
                delivery_radius_km=d.get("delivery_radius_km", Decimal("5")),
                commission_rate=d.get("commission_rate", Decimal("15")),
                commission_free_until=d.get("commission_free_until"),
                address=d.get("address", ""),
                country=country,
                status=Vendor.Status.APPROVED,
                reviewed_at=timezone.now(),
                reviewed_by=request.user,
            )
            record(request, "store.create", f"Created store {store.name} for {owner.phone}", store)
        return Response(store_detail(store), status=201)


class StoreView(ConsoleView):
    area = "stores"

    def get(self, request, pk):
        store = get_object_or_404(Vendor.objects.select_related("owner"), pk=pk)
        return Response(store_detail(store))

    def patch(self, request, pk):
        store = get_object_or_404(Vendor.objects.select_related("owner"), pk=pk)
        data = StoreInput(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        if "country" in d and d["country"] != store.country:
            # Its orders, statements and offers are in the old currency.
            if store.orders.exists():
                return Response({"country": ["A store that has taken orders can't change country."]}, status=400)
        changes = diff(store, d, EDITABLE + ["country"])
        with transaction.atomic():
            if "country" in d:
                store.country = d["country"]
            for field in EDITABLE:
                if field in d:
                    setattr(store, field, d[field])
            if "latitude" in d or "longitude" in d:
                lat = d.get("latitude", store.location.y)
                lng = d.get("longitude", store.location.x)
                changes["location"] = [f"{store.location.y},{store.location.x}", f"{lat},{lng}"]
                store.location = Point(lng, lat, srid=4326)
            if "owner_phone" in d:
                owner = _owner_for(d["owner_phone"], d.get("owner_name", ""), d.get("owner_country", "IQ"))
                if owner.pk != store.owner_id:
                    changes["owner"] = [store.owner.phone, owner.phone]
                    store.owner = owner
            store.save()
            if changes:
                record(request, "store.update", f"Edited store {store.name}", store, changes)
        return Response(store_detail(store))


class ReviewInput(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=Decimal("0"), max_value=Decimal("50"))


class StoreReviewView(ConsoleView):
    """POST {decision: approve|reject, reason?, commission_rate?}: answer a store application."""

    area = "stores"

    def post(self, request, pk):
        data = ReviewInput(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        reason = d.get("reason", "").strip()
        if d["decision"] == "reject" and not reason:
            return Response({"reason": ["Tell the owner why."]}, status=400)
        with transaction.atomic():
            store = get_object_or_404(Vendor.objects.select_for_update(), pk=pk)
            if d["decision"] == "approve":
                store.status = Vendor.Status.APPROVED
                store.rejection_reason = ""
                if "commission_rate" in d:
                    store.commission_rate = d["commission_rate"]
            else:
                store.status = Vendor.Status.REJECTED
                store.rejection_reason = reason
                store.is_open = False
            store.reviewed_at = timezone.now()
            store.reviewed_by = request.user
            store.save()
            record(
                request,
                f"store.{d['decision']}",
                f"{'Approved' if d['decision'] == 'approve' else 'Rejected'} store {store.name}",
                store,
                {"reason": reason} if reason else {},
            )
        return Response(store_detail(store))


# --- Menu ---------------------------------------------------------------------------


class ProductInput(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["name_ar", "name_ku", "name_en", "menu_section", "price", "unit_type", "is_available"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a price above zero.")
        currency = self.context.get("currency") or self.instance.vendor.currency
        return check_amount(value, currency)


def product_row(p, currency):
    return {
        "id": p.pk,
        "name_ar": p.name_ar,
        "name_ku": p.name_ku,
        "name_en": p.name_en,
        "menu_section": p.menu_section,
        "price": money(p.price, currency),
        "currency": currency,
        "unit_type": p.unit_type,
        "is_available": p.is_available,
    }


class StoreMenuView(ConsoleView):
    area = "stores"

    def get(self, request, pk):
        store = get_object_or_404(Vendor, pk=pk)
        return Response([product_row(p, store.currency) for p in store.products.filter(is_archived=False)])

    def post(self, request, pk):
        store = get_object_or_404(Vendor, pk=pk)
        data = ProductInput(data=request.data, context={"currency": store.currency})
        data.is_valid(raise_exception=True)
        product = data.save(vendor=store)
        record(request, "menu.add", f"Added {product.name_ar} to {store.name}", product)
        return Response(product_row(product, store.currency), status=201)


class ProductView(ConsoleView):
    area = "stores"

    def patch(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("vendor"), pk=pk, is_archived=False)
        data = ProductInput(product, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        changes = diff(product, data.validated_data, ProductInput.Meta.fields)
        data.save()
        if changes:
            record(request, "menu.update", f"Edited {product.name_ar} at {product.vendor.name}", product, changes)
        return Response(product_row(product, product.vendor.currency))

    def delete(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("vendor"), pk=pk, is_archived=False)
        if product.order_items.exists():
            product.is_archived = True
            product.save(update_fields=["is_archived"])
        else:
            product.delete()
        record(request, "menu.remove", f"Removed {product.name_ar} from {product.vendor.name}", product)
        return Response(status=204)


# --- Team ---------------------------------------------------------------------------


class MemberInput(serializers.Serializer):
    phone = serializers.CharField()
    country = CountryField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role = serializers.ChoiceField(choices=StoreMember.Role.choices, default=StoreMember.Role.CASHIER)


class StoreTeamView(ConsoleView):
    """GET: owner, members and open invites. POST: add someone directly (staff skip the invite)."""

    area = "stores"

    def get(self, request, pk):
        store = get_object_or_404(Vendor.objects.select_related("owner"), pk=pk)
        invites = [
            {"id": i.pk, "phone": i.phone, "name": i.name, "role": i.role, "created_at": i.created_at.isoformat()}
            for i in store.invites.filter(status="pending")
        ]
        return Response(
            {
                "owner": {"id": store.owner_id, "phone": store.owner.phone, "name": store.owner.name},
                "members": [
                    {"id": m.pk, "user": m.user_id, "phone": m.user.phone, "name": m.user.name, "role": m.role}
                    for m in store.members.select_related("user")
                ],
                "invites": invites,
            }
        )

    def post(self, request, pk):
        store = get_object_or_404(Vendor, pk=pk)
        data = MemberInput(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        try:
            user = _owner_for(d["phone"], d.get("name", ""), d.get("country", "IQ"))
        except serializers.ValidationError as error:
            return Response({"phone": error.detail["owner_phone"]}, status=400)
        if user.pk == store.owner_id or store.members.filter(user=user).exists():
            return Response({"error": "already_member", "detail": "Already on this store's team."}, status=400)
        member = StoreMember.objects.create(vendor=store, user=user, role=d["role"])
        record(request, "team.add", f"Added {user.phone} to {store.name} as {member.role}", member)
        return Response({"id": member.pk, "user": user.pk, "phone": user.phone, "name": user.name, "role": member.role}, status=201)


class RoleInput(serializers.Serializer):
    role = serializers.ChoiceField(choices=StoreMember.Role.choices)


class StoreMemberView(ConsoleView):
    area = "stores"

    def patch(self, request, pk, member_id):
        member = get_object_or_404(StoreMember.objects.select_related("user", "vendor"), pk=member_id, vendor_id=pk)
        data = RoleInput(data=request.data)
        data.is_valid(raise_exception=True)
        old = member.role
        member.role = data.validated_data["role"]
        member.save(update_fields=["role"])
        record(request, "team.role", f"{member.user.phone} at {member.vendor.name}: {old} → {member.role}", member)
        return Response({"id": member.pk, "role": member.role})

    def delete(self, request, pk, member_id):
        member = get_object_or_404(StoreMember.objects.select_related("user", "vendor"), pk=member_id, vendor_id=pk)
        record(request, "team.remove", f"Removed {member.user.phone} from {member.vendor.name}", member)
        member.delete()
        return Response(status=204)
