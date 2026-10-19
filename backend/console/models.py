from django.conf import settings
from django.db import models


class StaffProfile(models.Model):
    """
    A Wasel team member who uses the platform admin. Staff sign in with email,
    password and an authenticator code, separately from the phone-code login
    customers, captains and stores use. The role decides which areas they see.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        OPERATIONS = "operations", "Operations"
        SUPPORT = "support", "Support"
        FINANCE = "finance", "Finance"
        MARKETING = "marketing", "Marketing"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.SUPPORT)
    totp_secret = models.CharField(max_length=64, blank=True, help_text="Authenticator app secret (base32)")
    totp_enabled = models.BooleanField(default=False)
    # Last accepted authenticator time step, so one code can't be used twice.
    totp_last_step = models.BigIntegerField(default=0)
    failed_logins = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return f"{self.email} ({self.role})"


class AuditEntry(models.Model):
    """Who changed what in the platform admin, and when. Never edited or deleted."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=40, blank=True)
    target_id = models.CharField(max_length=40, blank=True)
    summary = models.CharField(max_length=300)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_email} {self.action}"
