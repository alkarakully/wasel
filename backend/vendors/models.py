from decimal import Decimal

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from accounts.models import money_field
from regions.regions import CHOICES as REGION_CHOICES
from regions.regions import quantize, region


class Vendor(models.Model):
    class Type(models.TextChoices):
        RESTAURANT = "restaurant", "Restaurant"
        SUPERMARKET = "supermarket", "Supermarket"
        CAFE = "cafe", "Cafés & sweets"
        PHARMACY = "pharmacy", "Pharmacy"
        CONVENIENCE = "convenience", "Convenience & household"
        FLOWERS = "flowers", "Flowers & gifts"

    class Cuisine(models.TextChoices):
        POPULAR = "popular", "Popular"
        EASTERN = "eastern", "Eastern"
        WESTERN = "western", "Western"
        FAST_FOOD = "fast_food", "Fast Food"
        SWEETS = "sweets", "Sweets"
        DRINKS = "drinks", "Drinks"

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vendors")
    name = models.CharField(max_length=150)
    # New stores wait for Wasel staff to approve them. Until then customers
    # never see them and they can't take orders.
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    rejection_reason = models.CharField(max_length=300, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    address = models.CharField(max_length=300, blank=True)
    # The country the store trades in: its currency, clock, week and fees.
    country = models.CharField(max_length=2, choices=REGION_CHOICES, default="IQ")
    type = models.CharField(max_length=12, choices=Type.choices, default=Type.RESTAURANT)
    cuisine = models.CharField(max_length=10, choices=Cuisine.choices, blank=True)
    location = models.PointField(geography=True)
    delivery_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5"))
    is_open = models.BooleanField(default=False)
    # e.g. {"sat": [["10:00", "23:00"]], "fri": [["14:00", "01:00"]]}
    opening_hours = models.JSONField(default=dict, blank=True)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("15"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percent of the food subtotal.",
    )
    commission_free_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def region(self):
        return region(self.country)

    @property
    def currency(self):
        return self.region.currency

    @property
    def tz(self):
        return self.region.tz

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    def commission_for(self, subtotal, at=None):
        """Commission owed on an order subtotal, 0 during the commission-free period."""
        at = at or timezone.now()
        if self.commission_free_until and at < self.commission_free_until:
            return Decimal(0)
        return quantize(Decimal(subtotal) * self.commission_rate / 100, self.currency)


class StoreMember(models.Model):
    """
    Someone who works at a store besides its owner. Managers run the menu,
    hours and reports; cashiers handle orders. Only the owner sees billing
    and manages the team.
    """

    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CASHIER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["vendor", "user"], name="one_membership_per_store")]

    def __str__(self):
        return f"{self.user} at {self.vendor} ({self.role})"


class StoreInvite(models.Model):
    """
    The owner asks someone to join the store's team. The person becomes a
    StoreMember only when they accept, the next time they sign in to the
    portal or the tablet app. The invite is for a phone number, so it works
    before that person has an account.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for an answer"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="invites")
    phone = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=10, choices=StoreMember.Role.choices, default=StoreMember.Role.CASHIER)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "phone"],
                condition=models.Q(status="pending"),
                name="one_open_invite_per_phone_per_store",
            )
        ]

    def __str__(self):
        return f"Invite for {self.phone} to {self.vendor} ({self.role}, {self.status})"


class Product(models.Model):
    class UnitType(models.TextChoices):
        ITEM = "item", "Per item"
        KG = "kg", "Per kg"

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    name_ar = models.CharField(max_length=150)
    name_ku = models.CharField(max_length=150, blank=True)
    name_en = models.CharField(max_length=150, blank=True)
    description_ar = models.CharField(max_length=300, blank=True)
    description_ku = models.CharField(max_length=300, blank=True)
    description_en = models.CharField(max_length=300, blank=True)
    menu_section = models.CharField(max_length=100, blank=True)
    # A square-ish JPEG, resized on upload (see vendors/images.py).
    image = models.ImageField(upload_to="products/", blank=True)
    price = money_field()
    unit_type = models.CharField(max_length=4, choices=UnitType.choices, default=UnitType.ITEM)
    is_available = models.BooleanField(default=True)
    # Removed from the menu but kept, because past orders point at it.
    is_archived = models.BooleanField(default=False)

    class Meta:
        # Menu order is the order the store added items; sections appear in
        # the order their first item was added.
        ordering = ["id"]

    def __str__(self):
        return self.name_en or self.name_ar


class ProductModifier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="modifiers")
    group_name = models.CharField(max_length=100, help_text="e.g. Size, Extras")
    name_ar = models.CharField(max_length=150)
    name_ku = models.CharField(max_length=150, blank=True)
    name_en = models.CharField(max_length=150, blank=True)
    price_delta = money_field(default=0)
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.group_name}: {self.name_en or self.name_ar}"


class Offer(models.Model):
    class Type(models.TextChoices):
        PERCENT = "percent", "Percent off"
        FIXED = "fixed", "Fixed amount off"
        FREE_DELIVERY = "free_delivery", "Free delivery"
        BOGO = "bogo", "Buy one, get one free"

    # Null vendor means a platform-wide offer, for every store in `country`.
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True, related_name="offers")
    # A store's offer follows its store's country; amounts are in that country's currency.
    country = models.CharField(max_length=2, choices=REGION_CHOICES, default="IQ")
    title = models.CharField(max_length=150)
    type = models.CharField(max_length=15, choices=Type.choices)
    # Buy one, get one free: the menu item it's on (sold per item, from the offer's store).
    product = models.ForeignKey(
        "Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="offers"
    )
    value = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    min_order = money_field(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_banner = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at"]

    def save(self, *args, **kwargs):
        if self.vendor_id:
            self.country = self.vendor.country
        super().save(*args, **kwargs)

    @property
    def currency(self):
        return region(self.country).currency

    def __str__(self):
        return self.title
