from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "app", "platform", "updated_at"]
    list_filter = ["app", "platform"]
    search_fields = ["user__phone"]
    raw_id_fields = ["user"]
