from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import WaselPlusSubscription


def start_wasel_plus_trial(user):
    """Give a newly verified customer free Wasel Plus for the trial period."""
    now = timezone.now()
    return WaselPlusSubscription.objects.create(
        user=user,
        status=WaselPlusSubscription.Status.TRIAL,
        trial_start_date=now,
        trial_end_date=now + timedelta(days=settings.WASEL_PLUS_TRIAL_DAYS),
    )
