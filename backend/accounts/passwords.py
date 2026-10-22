"""
Password sign-in with a phone number or a confirmed email.

People sign up with a login code and may then set a password. Forgot it?
Sign in with a code and set a new one. Five wrong passwords in a row lock
password sign-in for 15 minutes (codes still work).
"""

from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone

from .models import AuthToken, User
from .phone import InvalidPhone, normalize_phone

MAX_FAILURES = 5
LOCK = timedelta(minutes=15)


class LoginError(Exception):
    code = "invalid_login"


class Locked(LoginError):
    code = "locked"

    def __init__(self, retry_after):
        super().__init__("Too many wrong passwords. Wait, or sign in with a code.")
        self.retry_after = retry_after


class Disabled(LoginError):
    code = "account_disabled"


def find_account(login, country="IQ"):
    """The account a phone number (read in `country`) or an email belongs to, or None."""
    login = (login or "").strip()
    if "@" in login:
        return User.objects.filter(email__iexact=login).first()
    try:
        return User.objects.filter(phone=normalize_phone(login, country)).first()
    except InvalidPhone:
        return None


def sign_in(login, password, country="IQ"):
    """Return the user for a correct password; raise LoginError (always the same for unknown accounts)."""
    user = find_account(login, country)
    if user is None:
        make_password(password)  # same work as a real check, so timing doesn't tell
        raise LoginError("Wrong phone, email or password.")

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        now = timezone.now()
        if user.locked_until and user.locked_until > now:
            raise Locked(int((user.locked_until - now).total_seconds()) + 1)
        if not user.has_usable_password() or not user.check_password(password):
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILURES:
                user.locked_until = now + LOCK
                user.failed_logins = 0
            user.save(update_fields=["failed_logins", "locked_until"])
            wrong = True
        else:
            if user.failed_logins or user.locked_until:
                user.failed_logins, user.locked_until = 0, None
                user.save(update_fields=["failed_logins", "locked_until"])
            wrong = False
    # Raised after the commit, so the failure counts.
    if wrong:
        raise LoginError("Wrong phone, email or password.")
    if not user.is_active:
        raise Disabled("This account has been disabled.")
    return user


def set_password(user, password, keep=None):
    """
    Set a new password after Django's checks (raises ValidationError). Other
    devices are signed out; `keep` is the token of the device doing this.
    """
    validate_password(password, user)
    user.set_password(password)
    user.failed_logins, user.locked_until = 0, None
    user.save(update_fields=["password", "failed_logins", "locked_until"])
    AuthToken.objects.filter(user=user).exclude(pk=getattr(keep, "pk", None)).delete()
