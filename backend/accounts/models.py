from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
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
            # Customers and captains log in by WhatsApp/SMS code, not password.
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

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.name or self.phone} ({self.role})"


class PhoneOTP(models.Model):
    """A one-time login code sent to a phone number. Only a hash of the code is stored."""

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=64)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Code for {self.phone} via {self.channel}"


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
