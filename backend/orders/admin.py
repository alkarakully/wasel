from django.contrib.gis import admin

from .models import Order, OrderItem, Rating


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.GISModelAdmin):
    list_display = ["id", "customer", "vendor", "captain", "status", "payment_type", "total_amount", "created_at"]
    list_filter = ["status", "payment_type"]
    search_fields = ["customer__phone", "vendor__name"]
    inlines = [OrderItemInline]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["order", "vendor_stars", "captain_stars", "created_at"]
