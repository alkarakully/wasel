"""
Push notifications through Firebase Cloud Messaging (HTTP v1).

FCM delivers to Android directly and to iPhones through APNs, once an APNs
key is uploaded to the Firebase project. Without Firebase credentials the
console sender writes pushes to the log in development.

Code that wants to notify someone calls `notify(user_id, app, kind, **context)`;
the push is queued after the current transaction commits and sent by Celery.
"""

import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class PushError(Exception):
    """Sending failed for a reason that isn't the device's fault."""


@dataclass
class Push:
    title: str
    body: str
    data: dict = field(default_factory=dict)
    # Drop the push if it can't be delivered within this many seconds (offers).
    ttl_seconds: int | None = None
    urgent: bool = False


OK = "ok"
INVALID_TOKEN = "invalid_token"


class ConsoleSender:
    """Development only: writes pushes to the server log."""

    def send(self, fid, push):
        logger.warning("[DEV] Push to %s…: %s | %s | %s", fid[:12], push.title, push.body, push.data)
        return OK


class UnconfiguredSender:
    def send(self, fid, push):
        logger.warning("Push not sent: no push sender is configured.")
        return OK


class FcmSender:
    """Firebase Cloud Messaging HTTP v1, authenticated with a service account."""

    SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            settings.PUSH["FCM_CREDENTIALS_FILE"], scopes=[self.SCOPE]
        )
        self.project_id = settings.PUSH["FCM_PROJECT_ID"] or credentials.project_id
        self.session = AuthorizedSession(credentials)

    def message(self, fid, push):
        android = {"priority": "high" if push.urgent else "normal", "notification": {"sound": "default"}}
        apns = {
            "headers": {"apns-priority": "10" if push.urgent else "5"},
            "payload": {"aps": {"sound": "default"}},
        }
        if push.ttl_seconds is not None:
            android["ttl"] = f"{push.ttl_seconds}s"
            apns["headers"]["apns-expiration"] = str(int(time.time()) + push.ttl_seconds)
        return {
            "message": {
                "fid": fid,
                "notification": {"title": push.title, "body": push.body},
                # FCM data values must be strings.
                "data": {key: str(value) for key, value in push.data.items()},
                "android": android,
                "apns": apns,
            }
        }

    def send(self, fid, push):
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        try:
            response = self.session.post(url, json=self.message(fid, push), timeout=10)
        except Exception as error:
            raise PushError(f"FCM request failed: {error}") from error
        if response.status_code == 200:
            return OK
        error = response.json().get("error", {}) if response.content else {}
        codes = {detail.get("errorCode") for detail in error.get("details", [])}
        # The app was uninstalled or the FID is unknown: forget the device.
        if response.status_code == 404 or "UNREGISTERED" in codes or (
            response.status_code == 400 and "INVALID_ARGUMENT" in codes
        ):
            return INVALID_TOKEN
        raise PushError(f"FCM returned {response.status_code}: {error.get('message', '')}")


_sender = None


def get_sender():
    global _sender
    if _sender is None:
        _sender = import_string(settings.PUSH["SENDER"])()
    return _sender


def notify(user_id, app, kind, **context):
    """Queue a push to all of a user's devices for one app."""
    from .tasks import send_push  # tasks imports this module, so load it here

    transaction.on_commit(lambda: _enqueue(send_push, user_id, app, kind, context))


def _enqueue(task, user_id, app, kind, context):
    try:
        task.delay(user_id, app, kind, context)
    except Exception:
        # A push must never break the order flow.
        logger.exception("Could not queue %s push for user %s", kind, user_id)
