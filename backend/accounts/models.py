from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


def money_field(**kwargs):
    """Amounts in whole Iraqi dinars (IQD has no fractional unit in use)."""
    return models.DecimalField(max_digits=12, decimal_places=0, **kwargs)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Users must have a phone number")
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
    language_pref = models.CharField(max_length=2, choices=Language.choices, default=Language.ARABIC)
    # Cached total; WalletTransaction rows are the source of truth.
    wallet_balance = money_field(default=0)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.name or self.phone} ({self.role})"


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        TOP_UP = "top_up", "Top-up"
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"
        CASHBACK = "cashback", "Cashback"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="wallet_transactions")
    type = models.CharField(max_length=10, choices=Type.choices)
    # Signed: positive adds to the balance, negative spends from it.
    amount = money_field()
    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, null=True, blank=True, related_name="wallet_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} IQD for {self.user}"
