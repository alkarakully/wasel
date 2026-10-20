"""
Store self-service for the portal: the team, the menu and opening hours.

  GET/POST     /api/vendors/{id}/team/             owner (POST invites someone)
  PATCH/DELETE /api/vendors/{id}/team/{member}/    owner
  DELETE       /api/vendors/{id}/team/invites/{invite}/  owner (cancels an invite)
  POST         /api/vendors/{id}/products/         owner, manager
  PATCH/DELETE /api/products/{id}/                 owner, manager
  POST/DELETE  /api/products/{id}/image/           owner, manager (multipart field "image")
  GET/POST     /api/vendors/{id}/offers/           owner, manager
  PATCH/DELETE /api/vendors/{id}/offers/{offer}/   owner, manager
  PUT          /api/vendors/{id}/hours/            owner, manager
"""

import re
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.phone import InvalidPhone, normalize_phone
from accounts.serializers import CountryField
from regions.regions import as_api
from regions.serializers import check_amount

from . import access
from .images import BadImage, remove_product_image, save_product_image
from .models import Offer, Product, StoreInvite, StoreMember, Vendor
from .offers import check_offer, end_or_delete, offer_state, offer_value
from .onboarding import store_account_problem
from .serializers import ProductSerializer

DAYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _denied(area):
    detail = {
        "team": "Only the store owner can manage the team.",
        "menu": "Only the owner or a manager can change the menu.",
        "offers": "Only the owner or a manager can run offers.",
    }[area]
    return Response({"error": "not_allowed", "detail": detail}, status=403)


class StoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    area = "orders"

    def store(self, request, pk):
        """The store, or None when the user may not touch this area of it."""
        store = get_object_or_404(Vendor, pk=pk)
        return store if access.can(store, request.user, self.area) else None


# --- Team -----------------------------------------------------------------------


def _member_row(member):
    return {
        "id": member.pk,
        "user": member.user_id,
        "phone": member.user.phone,
        "name": member.user.name,
        "role": member.role,
    }


class AddMemberSerializer(serializers.Serializer):
    phone = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role = serializers.ChoiceField(choices=StoreMember.Role.choices, default=StoreMember.Role.CASHIER)
    # The phone's country; local numbers are read in it (Iraq by default).
    country = CountryField()

    def validate(self, data):
        try:
            data["phone"] = normalize_phone(data["phone"], data.get("country", "IQ"))
        except InvalidPhone as error:
            raise serializers.ValidationError({"phone": [str(error)]}) from error
        return data


def _invite_row(invite):
    return {
        "id": invite.pk,
        "phone": invite.phone,
        "name": invite.name,
        "role": invite.role,
        "created_at": invite.created_at.isoformat(),
    }


class TeamView(StoreView):
    """
    The owner invites managers and cashiers by phone. They join when they
    accept, the next time they sign in to the portal or the tablet app.
    """

    area = "team"

    def get(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("team")
        owner = store.owner
        members = store.members.select_related("user")
        invites = store.invites.filter(status=StoreInvite.Status.PENDING)
        return Response(
            {
                "owner": {"user": owner.pk, "phone": owner.phone, "name": owner.name, "role": access.OWNER},
                "members": [_member_row(m) for m in members],
                "invites": [_invite_row(i) for i in invites],
            }
        )

    def post(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("team")
        data = AddMemberSerializer(data=request.data)
        if not data.is_valid():
            return Response({"error": "invalid_phone", "detail": data.errors}, status=400)
        phone, role = data.validated_data["phone"], data.validated_data["role"]
        name = data.validated_data.get("name", "")

        user = User.objects.filter(phone=phone).first()
        if user is not None and store_account_problem(user):
            # A customer, captain or staff account can't double as store staff.
            return Response(
                {"error": "phone_in_use", "detail": "This number is already used by another kind of account."},
                status=400,
            )
        if user is not None and (user.pk == store.owner_id or store.members.filter(user=user).exists()):
            return Response({"error": "already_member", "detail": "This person is already on the team."}, status=400)
        try:
            with transaction.atomic():
                invite = StoreInvite.objects.create(
                    vendor=store, phone=phone, name=name, role=role, invited_by=request.user
                )
        except IntegrityError:
            # One open invite per number per store.
            return Response(
                {"error": "already_invited", "detail": "This number already has an invite waiting."}, status=400
            )
        return Response(_invite_row(invite), status=201)


class InviteView(StoreView):
    area = "team"

    def delete(self, request, pk, invite_id):
        store = self.store(request, pk)
        if store is None:
            return _denied("team")
        invite = get_object_or_404(StoreInvite, pk=invite_id, vendor=store, status=StoreInvite.Status.PENDING)
        invite.status = StoreInvite.Status.CANCELLED
        invite.save(update_fields=["status"])
        return Response(status=204)


class RoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=StoreMember.Role.choices)


class MemberView(StoreView):
    area = "team"

    def patch(self, request, pk, member_id):
        store = self.store(request, pk)
        if store is None:
            return _denied("team")
        member = get_object_or_404(StoreMember.objects.select_related("user"), pk=member_id, vendor=store)
        data = RoleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        member.role = data.validated_data["role"]
        member.save(update_fields=["role"])
        return Response(_member_row(member))

    def delete(self, request, pk, member_id):
        store = self.store(request, pk)
        if store is None:
            return _denied("team")
        get_object_or_404(StoreMember, pk=member_id, vendor=store).delete()
        return Response(status=204)


# --- Menu -------------------------------------------------------------------------


class ProductEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "name_ar", "name_ku", "name_en", "description_ar", "description_ku", "description_en",
            "menu_section", "price", "unit_type", "is_available",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a price above zero.")
        currency = self.context.get("currency") or self.instance.vendor.currency
        return check_amount(value, currency)

    def validate_name_ar(self, value):
        if not value.strip():
            raise serializers.ValidationError("Every item needs an Arabic name.")
        return value.strip()


class ProductsView(StoreView):
    area = "menu"

    def post(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("menu")
        data = ProductEditSerializer(data=request.data, context={"currency": store.currency})
        data.is_valid(raise_exception=True)
        product = data.save(vendor=store)
        return Response(ProductSerializer(product).data, status=201)


class ProductView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _product(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("vendor"), pk=pk, is_archived=False)
        return product if access.can(product.vendor, request.user, "menu") else None

    def patch(self, request, pk):
        product = self._product(request, pk)
        if product is None:
            return _denied("menu")
        data = ProductEditSerializer(product, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(ProductSerializer(product).data)

    def delete(self, request, pk):
        """Removes the item. One that was ever ordered is archived instead, so old orders keep it."""
        product = self._product(request, pk)
        if product is None:
            return _denied("menu")
        if product.order_items.exists():
            product.is_archived = True
            product.save(update_fields=["is_archived"])
        else:
            remove_product_image(product, save=False)
            product.delete()
        return Response(status=204)


class ProductImageView(ProductView):
    """POST a photo (multipart, field "image") to set or replace it; DELETE removes it."""

    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        product = self._product(request, pk)
        if product is None:
            return _denied("menu")
        upload = request.FILES.get("image")
        if upload is None:
            return Response({"error": "image_required", "detail": "Choose a photo."}, status=400)
        try:
            save_product_image(product, upload)
        except BadImage as error:
            return Response({"error": error.code, "detail": error.detail}, status=400)
        return Response(ProductSerializer(product).data)

    def delete(self, request, pk):
        product = self._product(request, pk)
        if product is None:
            return _denied("menu")
        remove_product_image(product)
        return Response(ProductSerializer(product).data)


# --- Offers -----------------------------------------------------------------------


class StoreOfferInput(serializers.ModelSerializer):
    # Bundles need a bundle definition, which isn't modelled yet; home banners are Wasel's call.
    type = serializers.ChoiceField(choices=[Offer.Type.PERCENT, Offer.Type.FIXED, Offer.Type.FREE_DELIVERY])

    class Meta:
        model = Offer
        fields = ["title", "type", "value", "min_order", "starts_at", "ends_at"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Give the offer a name customers will see.")
        return value.strip()

    def validate(self, data):
        if data.get("type") == Offer.Type.FREE_DELIVERY:
            data["value"] = Decimal(0)
        check_offer(data, self.instance, self.context["store"].country)
        return data


def _offer_row(offer, now=None):
    return {
        "id": offer.pk,
        "title": offer.title,
        "type": offer.type,
        "value": offer_value(offer),
        "min_order": as_api(offer.min_order, offer.currency),
        "currency": offer.currency,
        "starts_at": offer.starts_at.isoformat(),
        "ends_at": offer.ends_at.isoformat(),
        "is_banner": offer.is_banner,
        "state": offer_state(offer, now),
        "orders": getattr(offer, "order_count", None),
    }


class StoreOffersView(StoreView):
    """The store's offers, newest first (ended ones included); POST adds one."""

    area = "offers"

    def get(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("offers")
        now = timezone.now()
        offers = store.offers.annotate(order_count=Count("orders"))
        return Response([_offer_row(o, now) for o in offers])

    def post(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("offers")
        data = StoreOfferInput(data=request.data, context={"store": store})
        data.is_valid(raise_exception=True)
        offer = data.save(vendor=store)
        return Response(_offer_row(offer), status=201)


class StoreOfferView(StoreView):
    area = "offers"

    def _offer(self, request, pk, offer_id):
        store = self.store(request, pk)
        return store, (get_object_or_404(Offer, pk=offer_id, vendor=store) if store else None)

    def patch(self, request, pk, offer_id):
        store, offer = self._offer(request, pk, offer_id)
        if offer is None:
            return _denied("offers")
        data = StoreOfferInput(offer, data=request.data, partial=True, context={"store": store})
        data.is_valid(raise_exception=True)
        return Response(_offer_row(data.save()))

    def delete(self, request, pk, offer_id):
        """An offer nobody used is deleted; a used one ends now, so old orders keep it."""
        store, offer = self._offer(request, pk, offer_id)
        if offer is None:
            return _denied("offers")
        end_or_delete(offer)
        return Response(status=204)


# --- Opening hours ----------------------------------------------------------------


class HoursView(StoreView):
    """
    PUT {"sat": ["10:00", "23:30"], "fri": null, ...}: one opening per day,
    null when closed. A closing time before the opening means after midnight.
    """

    area = "menu"

    def put(self, request, pk):
        store = self.store(request, pk)
        if store is None:
            return _denied("menu")
        hours, errors = {}, {}
        for day in DAYS:
            value = request.data.get(day)
            if value is None:
                hours[day] = None
            elif (
                isinstance(value, list)
                and len(value) == 2
                and all(isinstance(t, str) and TIME.match(t) for t in value)
                and value[0] != value[1]
            ):
                hours[day] = value
            else:
                errors[day] = "Use two times like 10:00 and 23:30, or null when closed."
        if errors:
            return Response({"error": "invalid_hours", "detail": errors}, status=400)
        store.opening_hours = hours
        store.save(update_fields=["opening_hours"])
        return Response({"id": store.pk, "opening_hours": hours})
