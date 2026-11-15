from django.contrib import admin

from .models import NawsilPlusSubscription


@admin.register(NawsilPlusSubscription)
class NawsilPlusSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "trial_end_date", "renews_at"]
    list_filter = ["status"]
    search_fields = ["user__phone"]
