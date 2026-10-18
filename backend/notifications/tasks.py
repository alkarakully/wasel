import logging

from celery import shared_task

from accounts.models import User

from . import push
from .messages import render
from .models import Device

logger = logging.getLogger(__name__)

# Offers are useless once they expire; order updates can wait a little.
TTL = {"offer": 30}
URGENT = {"offer", "order_out_for_delivery", "store_new_order", "store_order_cancelled"}


@shared_task
def send_push(user_id, app, kind, context):
    """Send one notification to every device the user has for `app`."""
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return 0
    title, body = render(kind, user.language_pref, context)
    message = push.Push(
        title=title,
        body=body,
        data={"kind": kind, **{k: v for k, v in context.items() if k.endswith("_id")}},
        ttl_seconds=TTL.get(kind),
        urgent=kind in URGENT,
    )
    sent = 0
    for device in Device.objects.filter(user=user, app=app):
        try:
            result = push.get_sender().send(device.fid, message)
        except push.PushError:
            logger.exception("Push %s to device %s failed", kind, device.pk)
            continue
        if result == push.INVALID_TOKEN:
            device.delete()
        else:
            sent += 1
    return sent
