"""
Store self-service for the portal: the team, the menu and opening hours.

  GET/POST     /api/vendors/{id}/team/             owner (POST invites someone)
  PATCH/DELETE /api/vendors/{id}/team/{member}/    owner
  DELETE       /api/vendors/{id}/team/invites/{invite}/  owner (cancels an invite)
  POST         /api/vendors/{id}/products/         owner, manager
  PATCH/DELETE /api/products/{id}/                 owner, manager
  PUT          /api/vendors/{id}/hours/            owner, manager
"""

import re

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.phone import InvalidPhone, normalize_phone
from accounts.serializers import CountryField
from regions.serializers import check_amount

from . import access
from .models import Product, StoreInvite, StoreMember, Vendor
from .onboarding import store_account_problem
from .serializers import ProductSerializer

DAYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _denied(area):
    detail = {
        "team": "Only the store owner can manage the team.",
        "menu": "Only the owner or a manager can change the menu.",
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
        fields = ["name_ar", "name_ku", "name_en", "menu_section", "price", "unit_type", "is_available"]

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
            product.delete()
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
