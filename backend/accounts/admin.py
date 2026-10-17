from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PhoneOTP, User, WalletTransaction


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["phone", "name", "role", "language_pref", "wallet_balance", "is_active"]
    list_filter = ["role", "language_pref", "is_active", "is_staff"]
    search_fields = ["phone", "name"]
    fieldsets = [
        (None, {"fields": ["phone", "password"]}),
        ("Profile", {"fields": ["name", "role", "language_pref", "wallet_balance"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["phone", "name", "role", "password1", "password2"]}),
    ]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "amount", "order", "created_at"]
    list_filter = ["type"]
    search_fields = ["user__phone"]


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ["phone", "channel", "attempts", "created_at", "expires_at", "used_at"]
    list_filter = ["channel"]
    search_fields = ["phone"]
    # Codes are hashed; nothing here is worth editing.
    readonly_fields = [field.name for field in PhoneOTP._meta.fields]

    def has_add_permission(self, request):
        return False
