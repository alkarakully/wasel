from rest_framework.authentication import TokenAuthentication

from .models import AuthToken


class DeviceTokenAuthentication(TokenAuthentication):
    """`Authorization: Token <key>` with one token per signed-in device."""

    model = AuthToken
