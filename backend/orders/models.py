from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.models import money_field


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentType(models.TextChoices):
        COD = "cod", "Cash on delivery"
        CARD = "card", "Card"
        WALLET = "wallet", "Wasel Wallet"

    class PaymentStatus(models.TextChoices):
        # Cash is collected by the captain; card waits for the payment gateway.
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    class CancelledBy(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        VENDOR = "vendor", "Vendor"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="orders")
    captain = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    offer = models.ForeignKey("vendors.Offer", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices, default=PaymentType.COD)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    delivery_address = models.CharField(max_length=255)
    delivery_location = models.PointField(geography=True)

    subtotal = money_field(default=0)
    delivery_fee = money_field(default=0)
    service_fee = money_field(default=0)
    discount = money_field(default=0)
    tip = money_field(default=0)
    # Snapshot of the vendor's commission at checkout; never recalculated.
    commission_amount = money_field(default=0)
    total_amount = money_field(default=0)

    delivery_pin = models.CharField(max_length=6, blank=True)
    pin_attempts = models.PositiveSmallIntegerField(default=0)

    # Status timeline, used for tracking and for spotting stuck orders.
    accepted_at = models.DateTimeField(null=True, blank=True)
    estimated_ready_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=10, choices=CancelledBy.choices, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"

    def calculate_total(self):
        return self.subtotal + self.delivery_fee + self.service_fee + self.tip - self.discount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("vendors.Product", on_delete=models.PROTECT, related_name="order_items")
    # Decimal so per-kg supermarket items fit, e.g. 1.5 kg.
    quantity = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("1"))
    unit_price = money_field(help_text="Price at checkout, including chosen modifiers.")
    line_total = money_field()

    def __str__(self):
        return f"{self.quantity} × {self.product}"


class OrderItemModifier(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="modifiers")
    modifier = models.ForeignKey("vendors.ProductModifier", on_delete=models.PROTECT, related_name="+")
    price_delta = money_field(help_text="Modifier price at checkout.")

    def __str__(self):
        return str(self.modifier)


class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="rating")
    vendor_stars = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    captain_stars = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for {self.order}"


class StuckOrderAlert(models.Model):
    """Raised for support when an order sits in one step too long; resolved once it moves on."""

    class Reason(models.TextChoices):
        NOT_ACCEPTED = "not_accepted", "Store hasn't accepted"
        NOT_READY = "not_ready", "Past its ready time"
        NO_CAPTAIN = "no_captain", "No captain has taken it"
        NOT_PICKED_UP = "not_picked_up", "Ready but not picked up"
        DELIVERY_LATE = "delivery_late", "Out for delivery too long"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="stuck_alerts")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # At most one open alert per order and reason.
            models.UniqueConstraint(
                fields=["order", "reason"],
                condition=models.Q(resolved_at__isnull=True),
                name="one_open_alert_per_order_reason",
            )
        ]

    def __str__(self):
        return f"Order #{self.order_id}: {self.get_reason_display()}"
