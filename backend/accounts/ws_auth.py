from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


@database_sync_to_async
def _user_for_token(key):
    token = Token.objects.select_related("user").filter(key=key).first()
    if token is None or not token.user.is_active:
        return AnonymousUser()
    return token.user


class TokenAuthMiddleware(BaseMiddleware):
    """
    Signs a WebSocket in with the same API token the apps use for REST.

    Browsers can't set headers on a WebSocket, so the token comes from the
    `token` query parameter: ws://host/ws/orders/?token=<key>
    """

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        key = (query.get("token") or [""])[0]
        scope["user"] = await _user_for_token(key) if key else AnonymousUser()
        return await super().__call__(scope, receive, send)
