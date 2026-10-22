from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm

from .models import PhoneOTP, User, WalletTransaction
from .phone import InvalidPhone, normalize_phone, other_phone


def clean_phone_field(form, staff=False):
    """
    Store numbers the way login looks them up (+9647XXXXXXXXX), whatever was
    typed. Local numbers are read as Iraqi; other countries need their + code.
    App accounts sign in with a code sent to a mobile, so they need one; staff
    sign in to the admin with a password and may use any number.
    """
    raw = form.cleaned_data.get("phone")
    try:
        return normalize_phone(raw)
    except InvalidPhone as error:
        other = other_phone(raw)
        if staff and other:
            return other
        raise forms.ValidationError(str(error)) from error


class UserCreationForm(forms.ModelForm):
    """
    Add an account. Customers, captains and store owners sign in with a
    WhatsApp or email code (and may set their own password in the apps), so a
    password here is only for staff using this admin.
    """

    password1 = forms.CharField(
        label="Password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=(
            "Only for staff who sign in to this admin. Leave both fields blank for "
            "customers, captains and store owners: they sign in with a code."
        ),
    )
    password2 = forms.CharField(
        label="Password confirmation",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["phone", "name", "role"]
        help_texts = {"phone": "Any form works: 0770 123 4567, +964 770 123 4567, or Arabic digits."}

    def clean_phone(self):
        # A password means a staff login, which may use a non-Iraqi number.
        return clean_phone_field(self, staff=bool(self.data.get("password1")))

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get("password1"), cleaned.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "The two passwords don't match.")
            else:
                password_validation.validate_password(password1, self.instance)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        else:
            user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserEditForm(UserChangeForm):
    def clean_phone(self):
        staff = self.instance.is_staff or bool(self.data.get("is_staff"))
        return clean_phone_field(self, staff=staff)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserEditForm
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
        (None, {"classes": ["wide"], "fields": ["phone", "name", "role"]}),
        ("Admin password (staff only)", {"classes": ["wide"], "fields": ["password1", "password2"]}),
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
