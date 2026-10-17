import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wasel.settings")

# Load Django before importing anything that touches models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import path  # noqa: E402

from accounts.ws_auth import TokenAuthMiddleware  # noqa: E402
from orders.consumers import OrderUpdatesConsumer  # noqa: E402

# No Origin check: sockets sign in with an API token, not cookies, so another
# site can't open one as the user, and mobile apps don't send an Origin header.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TokenAuthMiddleware(
            URLRouter([path("ws/orders/", OrderUpdatesConsumer.as_asgi())])
        ),
    }
)
