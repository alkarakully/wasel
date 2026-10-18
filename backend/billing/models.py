from django.conf import settings
from django.db import models

from accounts.models import money_field


class Statement(models.Model):
    """
    One store's week (Saturday to Friday, Baghdad time). Wasel collects every
    payment (cash through captains, card and wallet in the app) and pays the
    store its food sales minus the store's own discounts and Wasel's
    commission. Made after the week ends; staff mark it paid.
    """

    class Status(models.TextChoices):
        DUE = "due", "Due"
        PAID = "paid", "Paid"

    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="statements")
    period_start = models.DateField(help_text="Saturday")
    period_end = models.DateField(help_text="Friday, included")
    orders_count = models.PositiveIntegerField(default=0)
    food_sales = money_field(default=0)
    store_discounts = money_field(default=0)
    commission = money_field(default=0)
    payout = money_field(default=0)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.DUE)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_reference = models.CharField(max_length=100, blank=True, help_text="Transfer or receipt number")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_start", "vendor__name"]
        constraints = [models.UniqueConstraint(fields=["vendor", "period_start"], name="one_statement_per_store_week")]

    def __str__(self):
        return f"{self.vendor} {self.period_start:%Y-%m-%d} ({self.get_status_display()})"
