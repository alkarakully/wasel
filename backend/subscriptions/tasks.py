import logging

from celery import shared_task
from django.utils import timezone

from orders.realtime import notify_user

from .models import NawsilPlusSubscription

logger = logging.getLogger(__name__)


@shared_task
def expire_nawsil_plus_trials():
    """
    Mark finished trials as expired and tell the user's app, so it can offer
    the paid plan. Pricing already stops the benefits at trial_end_date; this
    keeps the records and the app in step.
    """
    now = timezone.now()
    ended = list(
        NawsilPlusSubscription.objects.filter(
            status=NawsilPlusSubscription.Status.TRIAL, trial_end_date__lte=now
        ).values_list("pk", "user_id")
    )
    if not ended:
        return {"expired": 0}

    NawsilPlusSubscription.objects.filter(
        pk__in=[pk for pk, _ in ended], status=NawsilPlusSubscription.Status.TRIAL
    ).update(status=NawsilPlusSubscription.Status.EXPIRED)
    for _, user_id in ended:
        notify_user(user_id, {"type": "nawsil_plus.trial_ended"})

    logger.warning("Expired %d Nawsil Plus trials", len(ended))
    return {"expired": len(ended)}
