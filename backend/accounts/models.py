import binascii
import os

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .phone import InvalidPhone, country_of, normalize_phone, other_phone


def money_field(**kwargs):
    """
    An amount in the currency of its store, order or wallet: whole dinars in
    Iraq, halalas or fils elsewhere (up to 3 decimals for KWD, BHD and OMR).
    """
    return models.DecimalField(max_digits=15, decimal_places=3, **kwargs)


def currency_field(**kwargs):
    kwargs.setdefault("default", "IQD")
    return models.CharField(max_length=3, **kwargs)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Users must have a phone number")
        # Same form the login code flow uses, so the account can sign in.
        # Staff (createsuperuser) may use any number the admin can store.
        try:
            phone = normalize_phone(phone, extra_fields.get("country") or "IQ")
            extra_fields.setdefault("country", country_of(phone))
        except InvalidPhone:
            other = other_phone(phone)
            if not (other and (password or extra_fields.get("is_staff"))):
                raise
            phone = other
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # People sign up with a login code; they can set a password afterwards.
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        CAPTAIN = "captain", "Captain"
        VENDOR = "vendor", "Vendor"

    class Language(models.TextChoices):
        ARABIC = "ar", "العربية"
        KURDISH = "ku", "کوردی"
        ENGLISH = "en", "English"

    phone = models.CharField(max_length=20, unique=True)
    # A second way to sign in, once confirmed with a code sent to it. Stored lower-case.
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    # Where the account is from: its phone's country. The wallet is in this country's currency.
    country = models.CharField(max_length=2, default="IQ")
    language_pref = models.CharField(max_length=2, choices=Language.choices, default=Language.ARABIC)
    # Cached total; WalletTransaction rows are the source of truth.
    wallet_balance = money_field(default=0)

    @property
    def wallet_currency(self):
        from regions.regions import region

        return region(self.country).currency

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # Password sign-in locks for a while after too many wrong passwords.
    failed_logins = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_email_ignoring_case"),
        ]

    def __str__(self):
        return f"{self.name or self.phone} ({self.role})"


class PhoneOTP(models.Model):
    """
    A one-time code sent by WhatsApp to a phone number or by email to an
    address. Only a hash of the code is stored.

    A "login" code signs in (and on a phone, signs up). An "add_email" code
    confirms an address a signed-in person wants to add to their account.
    """

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"

    class Purpose(models.TextChoices):
        LOGIN = "login", "Sign in"
        ADD_EMAIL = "add_email", "Confirm a new email"

    # The phone number (E.164) or the email address (lower-case) the code went to.
    phone = models.CharField(max_length=254, db_index=True)
    code_hash = models.CharField(max_length=64)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    purpose = models.CharField(max_length=10, choices=Purpose.choices, default=Purpose.LOGIN)
    # Who asked to add the email (add_email codes only).
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Code for {self.phone} via {self.channel}"


class AuthToken(models.Model):
    """
    An API sign-in for one device. Each sign-in gets its own token, so
    logging out on one phone or tablet leaves the others signed in.
    """

    key = models.CharField(max_length=40, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_tokens")
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = binascii.hexlify(os.urandom(20)).decode()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sign-in for {self.user} ({self.created:%Y-%m-%d})"


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        TOP_UP = "top_up", "Top-up"
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"
        CASHBACK = "cashback", "Cashback"
        # Made by Wasel staff in the platform admin; the reason is in the audit log.
        ADJUSTMENT = "adjustment", "Adjustment"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="wallet_transactions")
    type = models.CharField(max_length=10, choices=Type.choices)
    currency = currency_field()
    # Signed: positive adds to the balance, negative spends from it.
    amount = money_field()
    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, null=True, blank=True, related_name="wallet_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} {self.currency} for {self.user}"
