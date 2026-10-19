"""
Phone login with one-time codes sent by WhatsApp (default) or SMS.

Codes are 6 digits, valid for a few minutes, stored only as an HMAC, and
locked after too many wrong guesses. If WhatsApp delivery fails the code is
sent by SMS instead.
"""

import hashlib
import hmac
import json
import logging
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.module_loading import import_string

from subscriptions.services import start_wasel_plus_trial

from .models import PhoneOTP, User
from .phone import country_of

logger = logging.getLogger(__name__)


class SendError(Exception):
    pass


class OTPError(Exception):
    code = "otp_error"


class TooSoon(OTPError):
    code = "too_soon"

    def __init__(self, retry_after):
        super().__init__(f"Wait {retry_after}s before requesting another code.")
        self.retry_after = retry_after


class TooManyRequests(OTPError):
    code = "too_many_requests"


class DeliveryFailed(OTPError):
    code = "delivery_failed"


class InvalidCode(OTPError):
    code = "invalid_code"


class AccountDisabled(OTPError):
    code = "account_disabled"


# --- Senders -----------------------------------------------------------------


class ConsoleSender:
    """Development only: writes the code to the server log."""

    def send(self, phone, code):
        logger.warning("[DEV] Wasel login code for %s: %s", phone, code)


class UnconfiguredSender:
    def send(self, phone, code):
        raise SendError("No sender is configured for this channel.")


class WhatsAppCloudSender:
    """
    Sends an authentication template through the WhatsApp Business Cloud API.

    Needs WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and an approved
    authentication template (WHATSAPP_TEMPLATE) with a copy-code button.
    """

    def send(self, phone, code):
        config = settings.WHATSAPP
        url = f"https://graph.facebook.com/{config['API_VERSION']}/{config['PHONE_NUMBER_ID']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "template",
            "template": {
                "name": config["TEMPLATE"],
                "language": {"code": config["TEMPLATE_LANGUAGE"]},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": code}]},
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": code}],
                    },
                ],
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {config['TOKEN']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status >= 300:
                    raise SendError(f"WhatsApp API returned {response.status}")
        except (urllib.error.URLError, TimeoutError) as error:
            raise SendError(f"WhatsApp API request failed: {error}") from error


def get_sender(channel):
    return import_string(settings.OTP["SENDERS"][channel])()


# --- Codes -------------------------------------------------------------------


def _hash(phone, code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def _new_code():
    return f"{secrets.randbelow(10**6):06d}"


@dataclass
class SentCode:
    channel: str
    expires_in: int
    resend_in: int


def request_code(phone, channel=PhoneOTP.Channel.WHATSAPP, country=None):
    """Create and send a login code. `phone` must already be normalized."""
    config = settings.OTP
    now = timezone.now()

    latest = PhoneOTP.objects.filter(phone=phone).first()
    if latest:
        wait = config["RESEND_SECONDS"] - int((now - latest.created_at).total_seconds())
        if wait > 0:
            raise TooSoon(wait)

    sent_last_hour = PhoneOTP.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1)).count()
    if sent_last_hour >= config["MAX_PER_HOUR"]:
        raise TooManyRequests("Too many codes requested for this number. Try again later.")

    code = _new_code()
    # WhatsApp first when asked for; SMS is always the fallback.
    channels = [channel] if channel == PhoneOTP.Channel.SMS else [channel, PhoneOTP.Channel.SMS]
    for attempt in channels:
        try:
            get_sender(attempt).send(phone, code)
        except SendError as error:
            logger.warning("Sending code to %s by %s failed: %s", phone, attempt, error)
            continue
        PhoneOTP.objects.create(
            phone=phone,
            code_hash=_hash(phone, code),
            channel=attempt,
            expires_at=now + timedelta(seconds=config["CODE_TTL_SECONDS"]),
        )
        return SentCode(attempt, config["CODE_TTL_SECONDS"], config["RESEND_SECONDS"])

    raise DeliveryFailed("We could not send a code to this number. Try again later.")


def verify_code(phone, code, country=None):
    """
    Check a code and return (user, created). Creates a customer account the
    first time a number logs in. Raises InvalidCode for any failure so callers
    cannot tell a wrong code from an expired or locked one.
    """
    now = timezone.now()
    # Raise only after the transaction commits, so a wrong guess still
    # counts towards the attempt limit.
    with transaction.atomic():
        otp = (
            PhoneOTP.objects.select_for_update()
            .filter(phone=phone, used_at__isnull=True, expires_at__gt=now)
            .first()
        )
        if otp is None or otp.attempts >= settings.OTP["MAX_ATTEMPTS"]:
            valid = False
        elif hmac.compare_digest(otp.code_hash, _hash(phone, str(code).strip())):
            otp.used_at = now
            otp.save(update_fields=["used_at"])
            valid = True
        else:
            PhoneOTP.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
            valid = False

    if not valid:
        raise InvalidCode("The code is wrong or has expired.")

    user = User.objects.filter(phone=phone).first()
    if user is None:
        # The account belongs to the number's country (its wallet currency).
        user = User.objects.create_user(phone=phone, country=country_of(phone))
        start_wasel_plus_trial(user)
        return user, True
    if not user.is_active:
        raise AccountDisabled("This account has been disabled.")
    return user, False
