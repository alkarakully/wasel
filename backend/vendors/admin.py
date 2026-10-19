from django.contrib.gis import admin

from .models import Offer, Product, ProductModifier, StoreInvite, Vendor


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ["name_ar", "name_en", "menu_section", "price", "unit_type", "is_available"]


@admin.register(Vendor)
class VendorAdmin(admin.GISModelAdmin):
    list_display = ["name", "status", "type", "cuisine", "is_open", "commission_rate", "commission_free_until"]
    list_filter = ["status", "type", "cuisine", "is_open"]
    search_fields = ["name", "owner__phone"]
    readonly_fields = ["reviewed_at", "reviewed_by"]
    inlines = [ProductInline]

    def get_changeform_initial_data(self, request):
        # A store staff set up here themselves is approved; owners' own
        # applications are reviewed in /ops/.
        return {"status": Vendor.Status.APPROVED, **super().get_changeform_initial_data(request)}


class ProductModifierInline(admin.TabularInline):
    model = ProductModifier
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["__str__", "vendor", "menu_section", "price", "unit_type", "is_available"]
    list_filter = ["unit_type", "is_available"]
    search_fields = ["name_ar", "name_en", "vendor__name"]
    inlines = [ProductModifierInline]


@admin.register(StoreInvite)
class StoreInviteAdmin(admin.ModelAdmin):
    list_display = ["phone", "vendor", "role", "status", "created_at", "answered_at"]
    list_filter = ["status", "role"]
    search_fields = ["phone", "vendor__name"]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["title", "vendor", "type", "value", "starts_at", "ends_at", "is_banner"]
    list_filter = ["type", "is_banner"]
