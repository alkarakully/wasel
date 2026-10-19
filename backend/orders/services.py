import secrets

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import F

from accounts.models import User, WalletTransaction
from notifications.push import notify
from vendors import access

from .models import Order, OrderItem, OrderItemModifier
from .pricing import PricingError, build_quote


def place_order(customer, *, vendor, items, latitude, longitude, delivery_address, payment_type, offer=None, tip=0):
    """
    Price the cart and create the order with snapshots of every price.
    Wallet orders are paid immediately; cash and card orders stay pending.
    """
    point = Point(longitude, latitude, srid=4326)

    with transaction.atomic():
        quote = build_quote(customer, vendor, items, point, offer_id=offer, tip=tip)
        currency = quote.vendor.currency

        payment_status = Order.PaymentStatus.PENDING
        if payment_type == Order.PaymentType.WALLET:
            # Lock the row so two orders at once can't spend the same balance.
            wallet = User.objects.select_for_update().only("wallet_balance", "country").get(pk=customer.pk)
            # The wallet holds its owner's country's currency; it can't pay for orders in another.
            if wallet.wallet_currency != currency:
                raise PricingError(
                    "wallet_currency_mismatch",
                    f"Your Wasel Wallet is in {wallet.wallet_currency}; this store charges in {currency}.",
                )
            if wallet.wallet_balance < quote.total_amount:
                raise PricingError("insufficient_wallet_balance", "Your Wasel Wallet balance is too low for this order.")
            payment_status = Order.PaymentStatus.PAID

        order = Order.objects.create(
            customer=customer,
            vendor=quote.vendor,
            offer=quote.offer,
            payment_type=payment_type,
            payment_status=payment_status,
            delivery_address=delivery_address,
            delivery_location=point,
            currency=currency,
            subtotal=quote.subtotal,
            delivery_fee=quote.delivery_fee,
            service_fee=quote.service_fee,
            discount=quote.discount,
            tip=quote.tip,
            commission_amount=quote.commission_amount,
            total_amount=quote.total_amount,
            delivery_pin=f"{secrets.randbelow(10_000):04d}",
        )

        for line in quote.lines:
            order_item = OrderItem.objects.create(
                order=order,
                product=line.product,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
            OrderItemModifier.objects.bulk_create(
                OrderItemModifier(order_item=order_item, modifier=modifier, price_delta=modifier.price_delta)
                for modifier in line.modifiers
            )

        if payment_type == Order.PaymentType.WALLET:
            WalletTransaction.objects.create(
                user=customer,
                type=WalletTransaction.Type.PAYMENT,
                currency=currency,
                amount=-quote.total_amount,
                order=order,
            )
            User.objects.filter(pk=customer.pk).update(wallet_balance=F("wallet_balance") - quote.total_amount)

        # The store's tablets ring even if the app is closed; sent after commit.
        for user_id in access.staff_ids(order.vendor):
            notify(user_id, "store", "store_new_order", order_id=order.pk, store=order.vendor.name)

    return order
