from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import NawsilPlusSubscription


def start_nawsil_plus_trial(user):
    """Give a newly verified customer free Nawsil Plus for the trial period."""
    now = timezone.now()
    return NawsilPlusSubscription.objects.create(
        user=user,
        status=NawsilPlusSubscription.Status.TRIAL,
        trial_start_date=now,
        trial_end_date=now + timedelta(days=settings.NAWSIL_PLUS_TRIAL_DAYS),
    )
