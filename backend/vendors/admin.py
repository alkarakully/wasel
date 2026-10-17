from django.contrib.gis import admin

from .models import Offer, Product, ProductModifier, Vendor


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ["name_ar", "name_en", "menu_section", "price", "unit_type", "is_available"]


@admin.register(Vendor)
class VendorAdmin(admin.GISModelAdmin):
    list_display = ["name", "type", "cuisine", "is_open", "commission_rate", "commission_free_until"]
    list_filter = ["type", "cuisine", "is_open"]
    search_fields = ["name", "owner__phone"]
    inlines = [ProductInline]


class ProductModifierInline(admin.TabularInline):
    model = ProductModifier
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["__str__", "vendor", "menu_section", "price", "unit_type", "is_available"]
    list_filter = ["unit_type", "is_available"]
    search_fields = ["name_ar", "name_en", "vendor__name"]
    inlines = [ProductModifierInline]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["title", "vendor", "type", "value", "starts_at", "ends_at", "is_banner"]
    list_filter = ["type", "is_banner"]
