from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from accounts.models import money_field


class Vendor(models.Model):
    class Type(models.TextChoices):
        RESTAURANT = "restaurant", "Restaurant"
        SUPERMARKET = "supermarket", "Supermarket"

    class Cuisine(models.TextChoices):
        POPULAR = "popular", "Popular"
        EASTERN = "eastern", "Eastern"
        WESTERN = "western", "Western"
        FAST_FOOD = "fast_food", "Fast Food"
        SWEETS = "sweets", "Sweets"
        DRINKS = "drinks", "Drinks"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vendors")
    name = models.CharField(max_length=150)
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

    def commission_for(self, subtotal, at=None):
        """Commission owed on an order subtotal, 0 during the commission-free period."""
        at = at or timezone.now()
        if self.commission_free_until and at < self.commission_free_until:
            return Decimal(0)
        amount = Decimal(subtotal) * self.commission_rate / 100
        return amount.quantize(Decimal(1), rounding=ROUND_HALF_UP)


class Product(models.Model):
    class UnitType(models.TextChoices):
        ITEM = "item", "Per item"
        KG = "kg", "Per kg"

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    name_ar = models.CharField(max_length=150)
    name_ku = models.CharField(max_length=150, blank=True)
    name_en = models.CharField(max_length=150, blank=True)
    menu_section = models.CharField(max_length=100, blank=True)
    price = money_field()
    unit_type = models.CharField(max_length=4, choices=UnitType.choices, default=UnitType.ITEM)
    is_available = models.BooleanField(default=True)

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
        BUNDLE = "bundle", "Bundle deal"

    # Null vendor means a platform-wide offer.
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True, related_name="offers")
    title = models.CharField(max_length=150)
    type = models.CharField(max_length=15, choices=Type.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_order = money_field(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_banner = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title
