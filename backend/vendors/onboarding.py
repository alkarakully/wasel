"""
Self-service onboarding: people apply to sell on Wasel and answer team invites.

  GET  /api/store-applications/                 your stores in every state, and whether you may apply
  POST /api/store-applications/                 apply with a store: your first one, or another branch
  GET  /api/store-invites/                      team invites waiting for you
  POST /api/store-invites/{id}/accept/          join that store's team
  POST /api/store-invites/{id}/decline/         say no

A new number verifies with the login code first, which makes a customer
account; applying or accepting an invite turns a fresh customer account (no
orders, no wallet history) into a store account. Accounts with a customer
history, captains and staff can't double as store accounts.

Stores start out pending; Wasel staff approve or reject them from /ops/.
"""

from decimal import Decimal

from django.contrib.gis.geos import Point
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from regions.regions import CODES as REGION_CODES
from regions.regions import region, where
from subscriptions.models import WaselPlusSubscription

from . import access
from .models import StoreInvite, StoreMember, Vendor

# Pending applications an approved owner may have at once (new branches).
MAX_PENDING = 3


# --- Store accounts ---------------------------------------------------------------


def store_account_problem(user):
    """None when the account can work at a store (now or once converted), else an error code."""
    if user.is_staff or user.is_superuser or user.role == User.Role.CAPTAIN:
        return "phone_in_use"
    if user.role == User.Role.CUSTOMER and (user.orders.exists() or user.wallet_transactions.exists()):
        return "phone_in_use"
    return None


def make_store_account(user, name=""):
    """Turn a fresh customer account into a store account. Call after store_account_problem() is None."""
    fields = []
    if user.role != User.Role.VENDOR:
        user.role = User.Role.VENDOR
        fields.append("role")
        # The free Wasel Plus trial is for customers.
        WaselPlusSubscription.objects.filter(user=user, status=WaselPlusSubscription.Status.TRIAL).update(
            status=WaselPlusSubscription.Status.EXPIRED, trial_end_date=timezone.now()
        )
    if name and not user.name:
        user.name = name
        fields.append("name")
    if fields:
        user.save(update_fields=fields)


# --- Applications -------------------------------------------------------------------


def application_row(store):
    return {
        "id": store.pk,
        "name": store.name,
        "type": store.type,
        "cuisine": store.cuisine,
        "address": store.address,
        "latitude": store.location.y,
        "longitude": store.location.x,
        "delivery_radius_km": str(store.delivery_radius_km.normalize()),
        "country": store.country,
        "currency": store.currency,
        "status": store.status,
        "rejection_reason": store.rejection_reason,
        "created_at": store.created_at.isoformat(),
        "reviewed_at": store.reviewed_at.isoformat() if store.reviewed_at else None,
    }


def apply_problem(user):
    """Why the user can't apply for a store right now, or None."""
    if problem := store_account_problem(user):
        return problem
    pending = Vendor.objects.filter(owner=user, status=Vendor.Status.PENDING).count()
    if access.is_approved_owner(user):
        return "too_many_applications" if pending >= MAX_PENDING else None
    # Before the first store is approved, one application at a time.
    return "application_pending" if pending else None


OUTSIDE = "Wasel doesn't run in this area yet. Check the map spot."


class ApplicationSerializer(serializers.Serializer):
    owner_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    name = serializers.CharField(max_length=150)
    type = serializers.ChoiceField(choices=Vendor.Type.choices)
    cuisine = serializers.ChoiceField(choices=Vendor.Cuisine.choices, required=False, allow_blank=True)
    address = serializers.CharField(max_length=300)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    # Where the store trades; guessed from the map spot when left out.
    country = serializers.ChoiceField(choices=REGION_CODES, required=False)
    delivery_radius_km = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal("1"), max_value=Decimal("30"), default=Decimal("5")
    )

    def validate_latitude(self, value):
        # A quick first check, so it's reported alongside other mistakes; validate() checks the country.
        if not any(region(code).bounds[0] <= value <= region(code).bounds[2] for code in REGION_CODES):
            raise serializers.ValidationError(OUTSIDE)
        return value

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter the store's name.")
        return value.strip()

    def validate_address(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter the store's address.")
        return value.strip()

    def validate(self, data):
        # Only restaurants have a cuisine.
        if data["type"] != Vendor.Type.RESTAURANT:
            data["cuisine"] = ""
        # The spot must be in a country Wasel runs in, so a slip of the map doesn't put the store abroad.
        country = data.get("country") or where(data["latitude"], data["longitude"])
        if country is None or not region(country).contains(data["latitude"], data["longitude"]):
            raise serializers.ValidationError({"latitude": OUTSIDE})
        data["country"] = country
        if not (data.get("owner_name") or "").strip() and not self.context["user"].name:
            raise serializers.ValidationError({"owner_name": "Enter your name."})
        return data


class ApplicationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stores = access.applications_for(request.user).order_by("-created_at")
        problem = apply_problem(request.user)
        return Response(
            {
                "can_apply": problem is None,
                "reason": problem,
                "applications": [application_row(s) for s in stores],
            }
        )

    def post(self, request):
        data = ApplicationSerializer(data=request.data, context={"user": request.user})
        if not data.is_valid():
            return Response({"error": "invalid_application", "detail": data.errors}, status=400)
        values = data.validated_data
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if problem := apply_problem(user):
                return Response({"error": problem, "detail": _apply_detail(problem)}, status=400)
            make_store_account(user, values.get("owner_name", "").strip())
            store = Vendor.objects.create(
                owner=user,
                name=values["name"],
                type=values["type"],
                cuisine=values.get("cuisine", ""),
                address=values["address"],
                location=Point(values["longitude"], values["latitude"], srid=4326),
                delivery_radius_km=values["delivery_radius_km"],
                country=values["country"],
                status=Vendor.Status.PENDING,
            )
        return Response(application_row(store), status=201)


def _apply_detail(problem):
    return {
        "phone_in_use": "This number is already used by another kind of account.",
        "application_pending": "Your store is still waiting for approval.",
        "too_many_applications": "Wait for your other new branches to be reviewed first.",
    }[problem]


# --- Team invites (the invited person's side) -------------------------------------------


def _my_invites(user):
    return StoreInvite.objects.filter(
        phone=user.phone, status=StoreInvite.Status.PENDING, vendor__status=Vendor.Status.APPROVED
    ).select_related("vendor", "invited_by")


def invite_for_invitee(invite):
    inviter = invite.invited_by
    return {
        "id": invite.pk,
        "store": {"id": invite.vendor_id, "name": invite.vendor.name, "type": invite.vendor.type},
        "role": invite.role,
        "invited_by": (inviter.name or inviter.phone) if inviter else "",
        "created_at": invite.created_at.isoformat(),
    }


class MyInvitesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response([invite_for_invitee(i) for i in _my_invites(request.user)])


class AnswerInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    answer = None  # "accept" or "decline"

    def post(self, request, pk):
        with transaction.atomic():
            # Only invites to the caller's own number exist for them.
            invite = get_object_or_404(_my_invites(request.user).select_for_update(of=("self",)), pk=pk)
            now = timezone.now()
            if self.answer == "decline":
                invite.status, invite.answered_at = StoreInvite.Status.DECLINED, now
                invite.save(update_fields=["status", "answered_at"])
                return Response({"id": invite.pk, "status": invite.status})

            user = User.objects.select_for_update().get(pk=request.user.pk)
            if problem := store_account_problem(user):
                return Response(
                    {"error": problem, "detail": "This number is already used by another kind of account."},
                    status=400,
                )
            make_store_account(user, invite.name)
            store = invite.vendor
            if store.owner_id != user.pk:
                StoreMember.objects.get_or_create(vendor=store, user=user, defaults={"role": invite.role})
            invite.status, invite.answered_at = StoreInvite.Status.ACCEPTED, now
            invite.save(update_fields=["status", "answered_at"])
        return Response({"id": invite.pk, "status": invite.status, "store": store.pk, "role": invite.role})
