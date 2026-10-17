from django.contrib import admin

from .models import WaselPlusSubscription


@admin.register(WaselPlusSubscription)
class WaselPlusSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "trial_end_date", "renews_at"]
    list_filter = ["status"]
    search_fields = ["user__phone"]
