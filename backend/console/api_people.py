"""Customers, captains and store accounts; their wallets; Wasel staff; the audit log."""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from accounts.models import User, WalletTransaction
from orders.models import Order
from regions.regions import region
from regions.serializers import check_amount
from subscriptions.models import WaselPlusSubscription
from vendors.models import StoreMember, Vendor

from .access import ConsoleView
from .audit import record
from .common import iso, money, paged
from .models import AuditEntry, StaffProfile
from .staff import active_admins, create_staff

def user_row(u):
    return {
        "id": u.pk,
        "phone": u.phone,
        "name": u.name,
        "role": u.role,
        "is_active": u.is_active,
        "is_staff": u.is_staff,
        "country": u.country,
        "wallet_currency": u.wallet_currency,
        "wallet_balance": money(u.wallet_balance, u.wallet_currency),
        "orders": getattr(u, "order_count", None),
        "joined": u.date_joined.isoformat(),
    }


class UsersView(ConsoleView):
    """GET ?role=&q=&active=&page=: app accounts (customers, captains, stores), newest first."""

    area = "people"

    def get(self, request):
        p = request.query_params
        users = User.objects.filter(is_staff=False).annotate(order_count=Count("orders")).order_by("-date_joined")
        if p.get("role") in User.Role.values:
            users = users.filter(role=p["role"])
        if p.get("active") in ("0", "1"):
            users = users.filter(is_active=p["active"] == "1")
        if q := p.get("q", "").strip():
            users = users.filter(Q(phone__icontains=q.lstrip("0")) | Q(name__icontains=q))
        counts = dict(
            User.objects.filter(is_staff=False).values_list("role").annotate(n=Count("id")).values_list("role", "n")
        )
        response = paged(self, request, users, user_row)
        response.data["counts"] = {r: counts.get(r, 0) for r in User.Role.values}
        return response


def _user(pk):
    return get_object_or_404(User.objects.filter(is_staff=False, is_superuser=False), pk=pk)


class UserView(ConsoleView):
    area = "people"

    def get(self, request, pk):
        u = _user(pk)
        orders = Order.objects.filter(customer=u)
        spent = (
            orders.filter(status=Order.Status.DELIVERED, currency=u.wallet_currency).aggregate(t=Sum("total_amount"))["t"]
        )
        deliveries = Order.objects.filter(captain=u, status=Order.Status.DELIVERED)
        plus = WaselPlusSubscription.objects.filter(user=u).first()
        stores = [
            {"id": v.pk, "name": v.name, "role": "owner", "status": v.status} for v in Vendor.objects.filter(owner=u)
        ] + [
            {"id": m.vendor_id, "name": m.vendor.name, "role": m.role, "status": m.vendor.status}
            for m in StoreMember.objects.filter(user=u).select_related("vendor")
        ]
        return Response(
            {
                **user_row(u),
                "language": u.language_pref,
                "last_login": iso(u.last_login),
                "orders_count": orders.count(),
                "delivered_spend": money(spent, u.wallet_currency),
                "deliveries": deliveries.count(),
                "stores": stores,
                "plus": {"status": plus.status, "renews_at": iso(plus.renews_at), "trial_end": iso(plus.trial_end_date)}
                if plus
                else None,
                "recent_orders": [
                    {
                        "id": o.pk,
                        "status": o.status,
                        "store": o.vendor.name,
                        "currency": o.currency,
                        "total": money(o.total_amount, o.currency),
                        "created_at": o.created_at.isoformat(),
                    }
                    for o in Order.objects.filter(Q(customer=u) | Q(captain=u)).select_related("vendor").order_by("-created_at")[:10]
                ],
                "wallet": [
                    {
                        "id": t.pk,
                        "type": t.type,
                        "currency": t.currency,
                        "amount": money(t.amount, t.currency),
                        "order": t.order_id,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in u.wallet_transactions.all()[:20]
                ],
            }
        )


class ActiveInput(serializers.Serializer):
    is_active = serializers.BooleanField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class UserActiveView(ConsoleView):
    """POST {is_active, reason}: block or unblock an app account. Their apps sign out at once."""

    area = "people"

    def post(self, request, pk):
        u = _user(pk)
        data = ActiveInput(data=request.data)
        data.is_valid(raise_exception=True)
        u.is_active = data.validated_data["is_active"]
        u.save(update_fields=["is_active"])
        record(
            request,
            "user.unblock" if u.is_active else "user.block",
            f"{'Unblocked' if u.is_active else 'Blocked'} {u.phone}",
            u,
            {"reason": data.validated_data.get("reason", "")},
        )
        return Response(user_row(u))


class AdjustInput(serializers.Serializer):
    """An amount in the wallet's currency; the limit and decimals follow its country."""

    amount = serializers.DecimalField(max_digits=15, decimal_places=3)
    reason = serializers.CharField(max_length=255)

    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError("Enter an amount other than zero.")
        r = region(self.context["country"])
        if abs(value) > r.max_wallet_adjustment:
            raise serializers.ValidationError(f"At most {r.max_wallet_adjustment:,} {r.currency} at a time.")
        return check_amount(value, r.currency)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Say why.")
        return value.strip()


class WalletAdjustView(ConsoleView):
    """POST {amount, reason}: add to (positive) or take from (negative) a customer's wallet."""

    area = "money"

    def post(self, request, pk):
        with transaction.atomic():
            u = get_object_or_404(User.objects.select_for_update().filter(is_staff=False), pk=pk)
            data = AdjustInput(data=request.data, context={"country": u.country})
            data.is_valid(raise_exception=True)
            amount, reason = data.validated_data["amount"], data.validated_data["reason"]
            currency = u.wallet_currency
            if u.wallet_balance + amount < 0:
                return Response(
                    {
                        "error": "insufficient_balance",
                        "detail": f"The wallet only has {money(u.wallet_balance, currency)} {currency}.",
                    },
                    status=400,
                )
            entry = WalletTransaction.objects.create(
                user=u, type=WalletTransaction.Type.ADJUSTMENT, currency=currency, amount=amount
            )
            User.objects.filter(pk=u.pk).update(wallet_balance=F("wallet_balance") + amount)
            u.refresh_from_db(fields=["wallet_balance"])
            shown = money(abs(amount), currency)
            record(
                request,
                "wallet.adjust",
                f"{'Added' if amount > 0 else 'Took'} {shown} {currency} {'to' if amount > 0 else 'from'} {u.phone}",
                entry,
                {
                    "user": u.pk,
                    "amount": money(amount, currency),
                    "currency": currency,
                    "reason": reason,
                    "balance": money(u.wallet_balance, currency),
                },
            )
        return Response({"id": entry.pk, "wallet_balance": money(u.wallet_balance, currency), "currency": currency}, status=201)


# --- Wasel staff ------------------------------------------------------------------


def staff_row(p):
    return {
        "id": p.pk,
        "user": p.user_id,
        "email": p.email,
        "name": p.user.name,
        "role": p.role,
        "is_active": p.user.is_active,
        "two_factor": p.totp_enabled,
        "locked": bool(p.locked_until and p.locked_until > timezone.now()),
        "last_login": iso(p.user.last_login),
        "created_at": p.created_at.isoformat(),
    }


def _check_password(password, user=None):
    try:
        password_validation.validate_password(password, user)
    except ValidationError as error:
        raise serializers.ValidationError({"password": list(error.messages)}) from error


class NewStaffInput(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=StaffProfile.Role.choices)
    password = serializers.CharField(min_length=10, max_length=128, write_only=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if StaffProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Someone on the team already uses this email.")
        return value


class StaffListView(ConsoleView):
    area = "staff"

    def get(self, request):
        return Response([staff_row(p) for p in StaffProfile.objects.select_related("user")])

    def post(self, request):
        data = NewStaffInput(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        _check_password(d["password"])
        profile = create_staff(d["email"], d["name"], d["role"], d["password"])
        record(request, "staff.create", f"Added {profile.email} as {profile.role}", profile)
        return Response(staff_row(profile), status=201)


class StaffEditInput(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(choices=StaffProfile.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class StaffMemberView(ConsoleView):
    area = "staff"

    def patch(self, request, pk):
        profile = get_object_or_404(StaffProfile.objects.select_related("user"), pk=pk)
        data = StaffEditInput(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        is_self = profile.user_id == request.user.pk
        demoting = d.get("role", profile.role) != StaffProfile.Role.ADMIN or d.get("is_active") is False
        if is_self and ("role" in d and d["role"] != profile.role or d.get("is_active") is False):
            return Response({"error": "self_lockout", "detail": "You can't change your own role or turn yourself off."}, status=400)
        if (
            profile.role == StaffProfile.Role.ADMIN
            and demoting
            and not active_admins().exclude(pk=profile.pk).exists()
        ):
            return Response({"error": "last_admin", "detail": "Keep at least one active admin."}, status=400)
        changes = {}
        user = profile.user
        if "name" in d and d["name"] != user.name:
            changes["name"] = [user.name, d["name"]]
            user.name = d["name"]
        if "is_active" in d and d["is_active"] != user.is_active:
            changes["is_active"] = [user.is_active, d["is_active"]]
            user.is_active = d["is_active"]
        if "role" in d and d["role"] != profile.role:
            changes["role"] = [profile.role, d["role"]]
            profile.role = d["role"]
            profile.save(update_fields=["role"])
        user.save(update_fields=["name", "is_active"])
        if changes:
            record(request, "staff.update", f"Edited {profile.email}", profile, changes)
        return Response(staff_row(profile))


class StaffResetView(ConsoleView):
    """POST {what: "two_factor"|"password", password?}: help a teammate who lost their phone or password."""

    area = "staff"

    def post(self, request, pk):
        profile = get_object_or_404(StaffProfile.objects.select_related("user"), pk=pk)
        if profile.user_id == request.user.pk:
            return Response({"error": "self_reset", "detail": "Change your own password from your account menu."}, status=400)
        what = request.data.get("what")
        if what == "two_factor":
            profile.totp_secret, profile.totp_enabled, profile.totp_last_step = "", False, 0
            profile.save(update_fields=["totp_secret", "totp_enabled", "totp_last_step"])
            record(request, "staff.reset_2fa", f"Reset the authenticator for {profile.email}", profile)
        elif what == "password":
            password = request.data.get("password") or ""
            _check_password(password, profile.user)
            profile.user.set_password(password)  # also signs them out everywhere
            profile.user.save(update_fields=["password"])
            profile.failed_logins, profile.locked_until = 0, None
            profile.save(update_fields=["failed_logins", "locked_until"])
            record(request, "staff.reset_password", f"Set a new password for {profile.email}", profile)
        else:
            return Response({"what": ['Use "two_factor" or "password".']}, status=400)
        return Response(staff_row(profile))


class AuditView(ConsoleView):
    """GET ?q=&action=&actor=&page=: the audit log, newest first."""

    area = "audit"

    def get(self, request):
        p = request.query_params
        entries = AuditEntry.objects.all()
        if action := p.get("action", "").strip():
            entries = entries.filter(action__startswith=action)
        if actor := p.get("actor", "").strip():
            entries = entries.filter(actor_email__iexact=actor)
        if q := p.get("q", "").strip():
            entries = entries.filter(Q(summary__icontains=q) | Q(target_id=q))
        return paged(
            self,
            request,
            entries,
            lambda e: {
                "id": e.pk,
                "actor": e.actor_email,
                "action": e.action,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "summary": e.summary,
                "changes": e.changes,
                "ip": e.ip,
                "created_at": e.created_at.isoformat(),
            },
        )
