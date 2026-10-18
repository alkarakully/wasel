from django.contrib import admin

from .models import Statement


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ["vendor", "period_start", "period_end", "orders_count", "payout", "status", "paid_at"]
    list_filter = ["status", "period_start"]
    search_fields = ["vendor__name", "paid_reference"]
    readonly_fields = ["orders_count", "food_sales", "store_discounts", "commission", "payout", "created_at"]
