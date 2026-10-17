from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from . import otp
from .serializers import RequestCodeSerializer, UserSerializer, VerifyCodeSerializer


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
    return Response(data, status=status.HTTP_400_BAD_REQUEST)


class RequestCodeView(APIView):
    """POST {phone, channel?} sends a 6-digit login code by WhatsApp (default) or SMS."""

    # No session auth, so a logged-in admin browser doesn't trigger CSRF checks here.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_request"

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sent = otp.request_code(**serializer.validated_data)
        except otp.OTPError as error:
            return otp_error_response(error)
        return Response(
            {
                "phone": serializer.validated_data["phone"],
                "channel": sent.channel,
                "expires_in": sent.expires_in,
                "resend_in": sent.resend_in,
            }
        )


class VerifyCodeView(APIView):
    """POST {phone, code} returns an API token, creating the account on first login."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, created = otp.verify_code(**serializer.validated_data)
        except otp.OTPError as error:
            return otp_error_response(error)
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "is_new_user": created, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


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
    """POST deletes the caller's API token."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
