from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import otp, passwords
from .models import AuthToken
from .serializers import (
    EmailCodeSerializer,
    EmailSerializer,
    PasswordLoginSerializer,
    RequestCodeSerializer,
    SetPasswordSerializer,
    UserSerializer,
    VerifyCodeSerializer,
)


def otp_error_response(error):
    data = {"error": error.code, "detail": str(error)}
    if isinstance(error, otp.TooSoon):
        data["retry_after"] = error.retry_after
        return Response(data, status=status.HTTP_429_TOO_MANY_REQUESTS, headers={"Retry-After": str(error.retry_after)})
    if isinstance(error, otp.TooManyRequests):
        return Response(data, status=status.HTTP_429_TOO_MANY_REQUESTS)
    if isinstance(error, otp.DeliveryFailed):
        return Response(data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(error, otp.AccountDisabled):
        return Response(data, status=status.HTTP_403_FORBIDDEN)
    if isinstance(error, (otp.NoAccount, otp.EmailTaken)):
        return Response(data, status=status.HTTP_409_CONFLICT if isinstance(error, otp.EmailTaken) else 404)
    return Response(data, status=status.HTTP_400_BAD_REQUEST)


def signed_in(user, created=False):
    """A new token for this device, with the account."""
    token = AuthToken.objects.create(user=user)
    return Response(
        {"token": token.key, "is_new_user": created, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


class RequestCodeView(APIView):
    """POST {phone, country} sends a 6-digit code by WhatsApp; {email} sends one to a confirmed email."""

    # No session auth, so a logged-in admin browser doesn't trigger CSRF checks here.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_request"

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            sent = otp.request_code(phone=data.get("phone"), email=data.get("email"))
        except otp.OTPError as error:
            return otp_error_response(error)
        return Response(
            {
                "phone": data.get("phone"),
                "email": data.get("email"),
                "channel": sent.channel,
                "expires_in": sent.expires_in,
                "resend_in": sent.resend_in,
            }
        )


class VerifyCodeView(APIView):
    """POST {phone or email, code} returns an API token, creating the account on a phone's first sign-in."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user, created = otp.verify_code(phone=data.get("phone"), code=data["code"], email=data.get("email"))
        except otp.OTPError as error:
            return otp_error_response(error)
        return signed_in(user, created)


class PasswordLoginView(APIView):
    """POST {login: phone or email, password, country} returns an API token."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "password_login"

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = passwords.sign_in(data["login"], data["password"], data["country"])
        except passwords.Locked as error:
            return Response(
                {"error": error.code, "detail": str(error), "retry_after": error.retry_after},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(error.retry_after)},
            )
        except passwords.Disabled as error:
            return Response({"error": error.code, "detail": str(error)}, status=status.HTTP_403_FORBIDDEN)
        except passwords.LoginError as error:
            return Response({"error": error.code, "detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return signed_in(user)


class PasswordView(APIView):
    """POST {password} sets or changes the signed-in person's password and signs out their other devices."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            passwords.set_password(request.user, serializer.validated_data["password"], keep=request.auth)
        except DjangoValidationError as error:
            return Response(
                {"error": "weak_password", "detail": " ".join(error.messages), "password": error.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(UserSerializer(request.user).data)


class EmailView(APIView):
    """POST {email} sends a code to confirm a new email; DELETE removes the email from the account."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "otp_request"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sent = otp.request_email_code(request.user, serializer.validated_data["email"])
        except otp.OTPError as error:
            return otp_error_response(error)
        return Response(
            {"email": serializer.validated_data["email"], "expires_in": sent.expires_in, "resend_in": sent.resend_in}
        )

    def delete(self, request):
        request.user.email = None
        request.user.save(update_fields=["email"])
        return Response(UserSerializer(request.user).data)


class ConfirmEmailView(APIView):
    """POST {email, code} makes the email a way to sign in."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = EmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = otp.confirm_email(request.user, data["email"], data["code"])
        except otp.OTPError as error:
            return otp_error_response(error)
        return Response(UserSerializer(user).data)


class MeView(APIView):
    """GET or PATCH the signed-in user's profile (name, language)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LogoutView(APIView):
    """POST signs this device out (its token only; other devices stay signed in)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, AuthToken):
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
