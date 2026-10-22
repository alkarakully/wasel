"""
One-time codes, sent by WhatsApp to a phone number or by email to an address.

  Sign in   a phone number (which also signs up a new customer), or an email
            already confirmed on an account.
  Add email a signed-in person confirms an address before it becomes a way
            to sign in.

Codes are 6 digits, valid for a few minutes, stored only as an HMAC, and
locked after too many wrong guesses. There is no SMS: if WhatsApp can't be
reached, people with an email on their account can sign in with that.
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


class NoAccount(OTPError):
    """No account has this email confirmed; sign up with a phone number first."""

    code = "no_account_for_email"


class EmailTaken(OTPError):
    code = "email_taken"


# --- Senders -----------------------------------------------------------------


class ConsoleSender:
    """Development only: writes the code to the server log."""

    def send(self, to, code, lang="ar"):
        logger.warning("[DEV] Wasel login code for %s: %s", to, code)


class UnconfiguredSender:
    def send(self, to, code, lang="ar"):
        raise SendError("No sender is configured for this channel.")


EMAIL_TEXT = {
    "ar": ("رمز الدخول إلى واصل: {code}", "رمز الدخول إلى واصل هو {code}\nيبقى صالحاً {minutes} دقائق. لا تشاركه مع أحد."),
    "ku": ("کۆدی چوونەژوورەوەی واصل: {code}", "کۆدی چوونەژوورەوەی واصل {code}ـە\nبۆ {minutes} خولەک کار دەکات. لەگەڵ کەس بەشی مەکە."),
    "en": ("Your Wasel code: {code}", "Your Wasel code is {code}\nIt works for {minutes} minutes. Don't share it with anyone."),
}


class EmailSender:
    """Sends the code by email through the SMTP server in settings (EMAIL_HOST...)."""

    def send(self, to, code, lang="ar"):
        from django.core.mail import send_mail

        subject, body = EMAIL_TEXT.get(lang, EMAIL_TEXT["ar"])
        minutes = settings.OTP["CODE_TTL_SECONDS"] // 60
        try:
            send_mail(
                subject.format(code=code),
                body.format(code=code, minutes=minutes),
                settings.DEFAULT_FROM_EMAIL,
                [to],
            )
        except Exception as error:  # SMTP and socket errors alike
            raise SendError(f"Email to {to} failed: {error}") from error


class WhatsAppCloudSender:
    """
    Sends an authentication template through the WhatsApp Business Cloud API.

    Needs WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID and an approved
    authentication template (WHATSAPP_TEMPLATE) with a copy-code button.
    """

    def send(self, phone, code, lang="ar"):
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


def _send(to, channel, purpose, user=None, lang="ar"):
    """Create and send a code to `to` (a normalized phone or a lower-case email)."""
    config = settings.OTP
    now = timezone.now()

    latest = PhoneOTP.objects.filter(phone=to).first()
    if latest:
        wait = config["RESEND_SECONDS"] - int((now - latest.created_at).total_seconds())
        if wait > 0:
            raise TooSoon(wait)

    sent_last_hour = PhoneOTP.objects.filter(phone=to, created_at__gte=now - timedelta(hours=1)).count()
    if sent_last_hour >= config["MAX_PER_HOUR"]:
        raise TooManyRequests("Too many codes requested. Try again later.")

    code = _new_code()
    try:
        get_sender(channel).send(to, code, lang)
    except SendError as error:
        logger.warning("Sending a code to %s by %s failed: %s", to, channel, error)
        raise DeliveryFailed("We could not send a code. Try again later.") from error
    PhoneOTP.objects.create(
        phone=to,
        code_hash=_hash(to, code),
        channel=channel,
        purpose=purpose,
        user=user,
        expires_at=now + timedelta(seconds=config["CODE_TTL_SECONDS"]),
    )
    return SentCode(channel, config["CODE_TTL_SECONDS"], config["RESEND_SECONDS"])


def _check(to, code, purpose, user=None):
    """Use up a matching code; False for a wrong, expired or locked one (all look the same)."""
    now = timezone.now()
    # Commit before answering, so a wrong guess still counts towards the attempt limit.
    with transaction.atomic():
        otp = (
            PhoneOTP.objects.select_for_update()
            .filter(phone=to, purpose=purpose, user=user, used_at__isnull=True, expires_at__gt=now)
            .first()
        )
        if otp is None or otp.attempts >= settings.OTP["MAX_ATTEMPTS"]:
            return False
        if hmac.compare_digest(otp.code_hash, _hash(to, str(code).strip())):
            otp.used_at = now
            otp.save(update_fields=["used_at"])
            return True
        PhoneOTP.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
        return False


def account_for_email(email):
    return User.objects.filter(email__iexact=email).first()


def request_code(phone=None, email=None, channel=PhoneOTP.Channel.WHATSAPP, country=None):
    """Send a sign-in code: by WhatsApp to a (normalized) phone, or by email to a confirmed address."""
    if email:
        user = account_for_email(email)
        if user is None:
            raise NoAccount("No account uses this email. Sign in with your phone number, then add your email.")
        return _send(email.lower(), PhoneOTP.Channel.EMAIL, PhoneOTP.Purpose.LOGIN, lang=user.language_pref)
    user = User.objects.filter(phone=phone).first()
    return _send(phone, PhoneOTP.Channel.WHATSAPP, PhoneOTP.Purpose.LOGIN, lang=user.language_pref if user else "ar")


def verify_code(phone=None, code="", email=None, country=None):
    """
    Check a sign-in code and return (user, created). A phone number's first
    sign-in creates a customer account. Raises InvalidCode for any failure,
    so callers can't tell a wrong code from an expired or locked one.
    """
    if not _check(email.lower() if email else phone, code, PhoneOTP.Purpose.LOGIN):
        raise InvalidCode("The code is wrong or has expired.")

    if email:
        user = account_for_email(email)
        if user is None:
            raise InvalidCode("The code is wrong or has expired.")
    else:
        user = User.objects.filter(phone=phone).first()
        if user is None:
            # The account belongs to the number's country (its wallet currency).
            user = User.objects.create_user(phone=phone, country=country_of(phone))
            start_wasel_plus_trial(user)
            return user, True
    if not user.is_active:
        raise AccountDisabled("This account has been disabled.")
    return user, False


def request_email_code(user, email):
    """Send a code to an address the signed-in `user` wants to add."""
    email = email.lower()
    other = account_for_email(email)
    if other is not None and other.pk != user.pk:
        raise EmailTaken("Another account already uses this email.")
    return _send(email, PhoneOTP.Channel.EMAIL, PhoneOTP.Purpose.ADD_EMAIL, user=user, lang=user.language_pref)


def confirm_email(user, email, code):
    """Check the code and make `email` a way for `user` to sign in."""
    email = email.lower()
    if not _check(email, code, PhoneOTP.Purpose.ADD_EMAIL, user=user):
        raise InvalidCode("The code is wrong or has expired.")
    with transaction.atomic():
        other = User.objects.select_for_update().filter(email__iexact=email).exclude(pk=user.pk).first()
        if other is not None:
            raise EmailTaken("Another account already uses this email.")
        user.email = email
        user.save(update_fields=["email"])
    return user
