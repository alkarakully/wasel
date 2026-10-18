from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from accounts.models import User
from vendors import access

from .realtime import CAPTAINS_GROUP, SUPPORT_GROUP, user_group, vendor_group
from .serializers import LocationSerializer
from .tracking import update_captain_location

# Close code for "not signed in" (4000-4999 are free for applications).
UNAUTHORIZED = 4401


class OrderUpdatesConsumer(AsyncJsonWebsocketConsumer):
    """
    ws://host/ws/orders/?token=<key>

    One socket per signed-in user. Customers and captains get updates for
    their own orders, store owners for their stores' orders, and captains
    also get the list of orders waiting for a captain.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            # Accept first: a socket refused during the handshake reaches
            # browsers as a bare 1006, so the app couldn't tell "bad token"
            # from "network down".
            await self.accept()
            await self.close(code=UNAUTHORIZED)
            return

        self.groups_joined = [user_group(user.pk)]
        self.groups_joined += [vendor_group(pk) for pk in await self._owned_vendor_ids(user)]
        if user.role == User.Role.CAPTAIN:
            self.groups_joined.append(CAPTAINS_GROUP)
        if user.is_staff:
            self.groups_joined.append(SUPPORT_GROUP)

        for group in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "user_id": user.pk})

    async def disconnect(self, code):
        for group in getattr(self, "groups_joined", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        # A ping keeps mobile connections from idling out.
        if kind == "ping":
            await self.send_json({"type": "pong"})
        elif kind == "location":
            await self._captain_location(content)

    async def _captain_location(self, content):
        """Captains send {"type": "location", "lat": .., "lng": .., "heading"?: .., "speed"?: ..}."""
        user = self.scope["user"]
        if user.role != User.Role.CAPTAIN:
            await self.send_json({"type": "error", "error": "not_allowed", "detail": "Only captains send locations."})
            return
        serializer = LocationSerializer(data=content)
        if not serializer.is_valid():
            await self.send_json({"type": "error", "error": "invalid_location", "detail": serializer.errors})
            return
        await database_sync_to_async(update_captain_location)(user, **serializer.validated_data)

    async def order_event(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _owned_vendor_ids(self, user):
        # Owners and their team all follow the store's orders.
        return access.store_ids_for(user)
