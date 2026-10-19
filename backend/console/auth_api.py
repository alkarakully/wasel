"""
Platform admin sign-in: email and password, then a 6-digit authenticator code.
The first sign-in sets up the authenticator (scan a QR code, confirm a code).

  GET  /api/console/auth/session/    who's signed in (also sets the CSRF cookie)
  POST /api/console/auth/login/      {email, password}  -> next step: "code" or "setup"
  POST /api/console/auth/verify/     {code}             -> signed in
  POST /api/console/auth/logout/
  POST /api/console/auth/password/   {current, new}
"""

from datetime import timedelta

from django.contrib.auth import login, logout, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from . import totp
from .access import VERIFIED, areas_for, staff_profile
from .audit import record
from .models import StaffProfile

MAX_FAILURES = 5
LOCK = timedelta(minutes=15)
PENDING = "console_pending_user"
PENDING_AT = "console_pending_at"
PENDING_MINUTES = 5
SESSION_HOURS = 12


def me(profile):
    user = profile.user
    return {
        "id": user.pk,
        "email": profile.email,
        "name": user.name,
        "role": profile.role,
        "areas": areas_for(profile.role),
    }


class AuthView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.AllowAny]
    throttle_scope = "console_login"


@method_decorator(ensure_csrf_cookie, name="get")
class SessionView(AuthView):
    throttle_scope = None

    def get(self, request):
        profile = staff_profile(request)
        return Response({"user": me(profile) if profile else None})


def _failed(profile):
    profile.failed_logins += 1
    if profile.failed_logins >= MAX_FAILURES:
        profile.locked_until = timezone.now() + LOCK
        profile.failed_logins = 0
    profile.save(update_fields=["failed_logins", "locked_until"])


def _locked(profile):
    return profile.locked_until and profile.locked_until > timezone.now()


REFUSED = {"error": "invalid_login", "detail": "Wrong email or password."}
LOCKED = {"error": "locked", "detail": "Too many tries. Wait 15 minutes, or ask an admin."}


class LoginView(AuthView):
    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))
        profile = StaffProfile.objects.select_related("user").filter(email__iexact=email).first()
        # Same answer for unknown emails and wrong passwords.
        if profile is None or not profile.user.is_active or not profile.user.is_staff:
            return Response(REFUSED, status=400)
        if _locked(profile):
            return Response(LOCKED, status=429)
        if not profile.user.check_password(password):
            _failed(profile)
            return Response(REFUSED, status=400)

        profile.failed_logins = 0
        profile.save(update_fields=["failed_logins"])
        request.session.cycle_key()
        request.session[PENDING] = profile.user.pk
        request.session[PENDING_AT] = timezone.now().isoformat()
        if profile.totp_enabled:
            return Response({"next": "code"})
        # First sign-in: set up the authenticator app.
        if not profile.totp_secret:
            profile.totp_secret = totp.new_secret()
            profile.save(update_fields=["totp_secret"])
        return Response(
            {
                "next": "setup",
                "secret": profile.totp_secret,
                "uri": totp.provisioning_uri(profile.totp_secret, profile.email),
            }
        )


class VerifyView(AuthView):
    def post(self, request):
        user_id = request.session.get(PENDING)
        started = request.session.get(PENDING_AT)
        if not user_id or not started:
            return Response({"error": "start_again", "detail": "Sign in with your email and password first."}, status=400)
        if timezone.now() - timezone.datetime.fromisoformat(started) > timedelta(minutes=PENDING_MINUTES):
            request.session.pop(PENDING, None)
            return Response({"error": "start_again", "detail": "That took too long. Sign in again."}, status=400)

        profile = StaffProfile.objects.select_related("user").filter(user_id=user_id).first()
        if profile is None or not profile.user.is_active:
            return Response({"error": "start_again", "detail": "Sign in again."}, status=400)
        if _locked(profile):
            return Response(LOCKED, status=429)
        step = totp.verify(profile.totp_secret, request.data.get("code", ""), profile.totp_last_step)
        if step is None:
            _failed(profile)
            return Response({"error": "invalid_code", "detail": "That code isn't right. Use the newest one."}, status=400)

        first_time = not profile.totp_enabled
        profile.totp_enabled = True
        profile.totp_last_step = step
        profile.failed_logins = 0
        profile.save(update_fields=["totp_enabled", "totp_last_step", "failed_logins"])

        login(request, profile.user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop(PENDING, None)
        request.session.pop(PENDING_AT, None)
        request.session[VERIFIED] = profile.user.pk
        request.session.set_expiry(SESSION_HOURS * 3600)
        request.staff = profile
        record(request, "auth.login", f"{profile.email} signed in" + (" and set up 2FA" if first_time else ""), profile.user)
        return Response({"user": me(profile)})


class LogoutView(AuthView):
    throttle_scope = None

    def post(self, request):
        logout(request)
        return Response(status=204)


class PasswordView(AuthView):
    def post(self, request):
        profile = staff_profile(request)
        if profile is None:
            return Response({"error": "not_signed_in"}, status=403)
        current, new = str(request.data.get("current", "")), str(request.data.get("new", ""))
        if not profile.user.check_password(current):
            return Response({"error": "wrong_password", "detail": "Your current password isn't right."}, status=400)
        try:
            password_validation.validate_password(new, profile.user)
        except ValidationError as error:
            return Response({"error": "weak_password", "detail": " ".join(error.messages)}, status=400)
        profile.user.set_password(new)
        profile.user.save(update_fields=["password"])
        # Changing the password keeps this session but signs out the others.
        from django.contrib.auth import update_session_auth_hash

        update_session_auth_hash(request, profile.user)
        request.staff = profile
        record(request, "auth.password", f"{profile.email} changed their password", profile.user)
        return Response(status=204)
