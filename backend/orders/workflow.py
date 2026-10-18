"""
Order status flow.

    received ──accept──> preparing ──ready──> ready ──pickup──> out_for_delivery ──deliver(PIN)──> delivered
       │                     ▲                  ▲
       ├─cancel (customer)   └──── claim (any captain, while preparing or ready, once)
       └─reject (vendor)

Every step locks the order row, checks who is acting and what state the
order is in, then moves it on. Cancelled wallet orders are refunded.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import User, WalletTransaction
from notifications.push import notify

from .models import DispatchOffer, Order

MAX_PIN_ATTEMPTS = 5


class WorkflowError(Exception):
    code = "workflow_error"
    status = 400

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class NotAllowed(WorkflowError):
    code = "not_allowed"
    status = 403


class InvalidTransition(WorkflowError):
    code = "invalid_transition"
    status = 409


class AlreadyClaimed(WorkflowError):
    code = "already_claimed"
    status = 409


class WrongPin(WorkflowError):
    code = "wrong_pin"


class OfferedToAnother(WorkflowError):
    code = "offered_to_another"
    status = 409


class PinLocked(WorkflowError):
    code = "pin_locked"
    status = 423


def _lock(order_id):
    return Order.objects.select_for_update(of=("self",)).select_related("vendor").get(pk=order_id)


def _require_status(order, *allowed):
    if order.status not in allowed:
        raise InvalidTransition(f"Order #{order.pk} is {order.get_status_display().lower()}.")


def _require_vendor_owner(order, user):
    if order.vendor.owner_id != user.pk:
        raise NotAllowed("Only the store can do this.")


def _require_captain(order, user):
    if order.captain_id != user.pk:
        raise NotAllowed("Only the captain delivering this order can do this.")


def _notify_customer(order, kind, **context):
    """Push the customer's app; sent after the change commits."""
    notify(order.customer_id, "customer", kind, order_id=order.pk, store=order.vendor.name, **context)


def _refund_if_paid(order):
    if order.payment_type == Order.PaymentType.WALLET and order.payment_status == Order.PaymentStatus.PAID:
        WalletTransaction.objects.create(
            user_id=order.customer_id, type=WalletTransaction.Type.REFUND, amount=order.total_amount, order=order
        )
        User.objects.filter(pk=order.customer_id).update(wallet_balance=F("wallet_balance") + order.total_amount)
        order.payment_status = Order.PaymentStatus.REFUNDED


# --- Store ----------------------------------------------------------------------


@transaction.atomic
def accept(order_id, user, prep_minutes):
    order = _lock(order_id)
    _require_vendor_owner(order, user)
    _require_status(order, Order.Status.RECEIVED)
    now = timezone.now()
    order.status = Order.Status.PREPARING
    order.accepted_at = now
    order.estimated_ready_at = now + timedelta(minutes=prep_minutes)
    order.save()
    _notify_customer(order, "order_preparing", minutes=prep_minutes)
    return order


@transaction.atomic
def reject(order_id, user, reason):
    order = _lock(order_id)
    _require_vendor_owner(order, user)
    _require_status(order, Order.Status.RECEIVED)
    _cancel(order, Order.CancelledBy.VENDOR, reason)
    _notify_customer(order, "order_cancelled", reason=reason)
    return order


@transaction.atomic
def mark_ready(order_id, user):
    order = _lock(order_id)
    _require_vendor_owner(order, user)
    _require_status(order, Order.Status.PREPARING)
    order.status = Order.Status.READY
    order.ready_at = timezone.now()
    order.save()
    return order


# --- Customer -------------------------------------------------------------------


@transaction.atomic
def cancel(order_id, user, reason=""):
    order = _lock(order_id)
    if order.customer_id != user.pk:
        raise NotAllowed("Only the customer can cancel this order.")
    if order.status != Order.Status.RECEIVED:
        raise InvalidTransition("The store has already started this order, so it can't be cancelled in the app.")
    _cancel(order, Order.CancelledBy.CUSTOMER, reason)
    notify(order.vendor.owner_id, "store", "store_order_cancelled", order_id=order.pk, store=order.vendor.name)
    return order


def _cancel(order, by, reason):
    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.cancelled_by = by
    order.cancel_reason = reason
    _refund_if_paid(order)
    order.save()


# --- Captain --------------------------------------------------------------------


@transaction.atomic
def claim(order_id, user):
    if user.role != User.Role.CAPTAIN:
        raise NotAllowed("Only captains can take orders.")
    order = _lock(order_id)
    _require_status(order, Order.Status.PREPARING, Order.Status.READY)
    if order.captain_id is not None:
        if order.captain_id == user.pk:
            return order
        raise AlreadyClaimed("Another captain has taken this order.")
    offer = order.pending_offer()
    if offer is not None:
        if offer.captain_id != user.pk:
            raise OfferedToAnother("This order is being offered to another captain.")
        offer.status = DispatchOffer.Status.ACCEPTED
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at"])
    order.captain = user
    order.save()
    return order


@transaction.atomic
def pickup(order_id, user):
    order = _lock(order_id)
    _require_captain(order, user)
    _require_status(order, Order.Status.READY)
    order.status = Order.Status.OUT_FOR_DELIVERY
    order.picked_up_at = timezone.now()
    order.save()
    _notify_customer(order, "order_out_for_delivery")
    return order


def deliver(order_id, user, pin):
    """Finish the delivery once the customer's PIN matches. Wrong PINs are counted."""
    with transaction.atomic():
        order = _lock(order_id)
        _require_captain(order, user)
        _require_status(order, Order.Status.OUT_FOR_DELIVERY)
        if order.pin_attempts >= MAX_PIN_ATTEMPTS:
            raise PinLocked("Too many wrong PINs. Contact support to finish this delivery.")

        if str(pin).strip() != order.delivery_pin:
            # Saved before raising, outside the rollback below.
            Order.objects.filter(pk=order.pk).update(pin_attempts=F("pin_attempts") + 1)
            wrong = True
        else:
            order.status = Order.Status.DELIVERED
            order.delivered_at = timezone.now()
            if order.payment_type == Order.PaymentType.COD:
                # The captain collected the cash at the door.
                order.payment_status = Order.PaymentStatus.PAID
            order.save()
            _notify_customer(order, "order_delivered")
            wrong = False

    if wrong:
        remaining = MAX_PIN_ATTEMPTS - (order.pin_attempts + 1)
        raise WrongPin(f"Wrong PIN. {remaining} attempts left.")
    return order
