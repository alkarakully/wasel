from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Point
from django.test import TransactionTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from vendors.models import Product, Vendor
from wasel.asgi import application

IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


# TransactionTestCase: socket code reads the database from other threads, and
# order updates are sent on commit, so each test needs real commits.
@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class OrderUpdatesSocketTests(TransactionTestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000050")
        self.stranger = User.objects.create_user(phone="+9647700000051")
        self.owner = User.objects.create_user(phone="+9647800000052", role=User.Role.VENDOR)
        self.captain = User.objects.create_user(phone="+9647500000053", role=User.Role.CAPTAIN)
        self.vendor = Vendor.objects.create(
            owner=self.owner, name="Socket Grill", location=Point(44.4009, 33.3406, srid=4326), is_open=True
        )
        self.product = Product.objects.create(vendor=self.vendor, name_ar="تكة", price=9000)
        self.tokens = {user.pk: Token.objects.create(user=user).key for user in (self.customer, self.stranger, self.owner, self.captain)}
        self.sockets = []

    async def close_all(self):
        # Django test cases don't run asyncTearDown, so tests call this themselves.
        for socket in self.sockets:
            await socket.disconnect()

    async def connect(self, user=None, token=None):
        token = token if token is not None else self.tokens[user.pk]
        socket = WebsocketCommunicator(application, f"/ws/orders/?token={token}")
        connected, code = await socket.connect()
        if connected:
            self.sockets.append(socket)
            self.assertEqual((await socket.receive_json_from())["type"], "connected")
        return socket, connected, code

    # REST calls run in a worker thread, like a real request would.
    @database_sync_to_async
    def api(self, user, method, path, body=None):
        client = APIClient()
        client.force_authenticate(user)
        response = getattr(client, method)(path, body or {}, format="json")
        assert response.status_code < 300, response.content
        return response.json()

    async def place_order(self):
        return await self.api(
            self.customer,
            "post",
            "/api/orders/",
            {
                "vendor": self.vendor.pk,
                "items": [{"product": self.product.pk}],
                "delivery_latitude": 33.3496,
                "delivery_longitude": 44.4009,
                "delivery_address": "Karrada 52",
            },
        )

    async def test_rejects_missing_or_bad_token(self):
        for token in ["", "not-a-real-token"]:
            with self.subTest(token=token):
                socket = WebsocketCommunicator(application, f"/ws/orders/?token={token}")
                connected, _ = await socket.connect()
                self.assertTrue(connected)  # accepted, then closed with a reason
                self.assertEqual(await socket.receive_output(), {"type": "websocket.close", "code": 4401})

    async def test_ping_pong(self):
        socket, connected, _ = await self.connect(self.customer)
        self.assertTrue(connected)
        await socket.send_json_to({"type": "ping"})
        self.assertEqual(await socket.receive_json_from(), {"type": "pong"})
        await self.close_all()

    async def test_new_order_reaches_customer_with_pin_and_store_without(self):
        customer, _, _ = await self.connect(self.customer)
        store, _, _ = await self.connect(self.owner)
        stranger, _, _ = await self.connect(self.stranger)

        order = await self.place_order()

        to_customer = await customer.receive_json_from()
        self.assertEqual(to_customer["type"], "order.updated")
        self.assertEqual(to_customer["order"]["id"], order["id"])
        self.assertEqual(to_customer["order"]["delivery_pin"], order["delivery_pin"])

        to_store = await store.receive_json_from()
        self.assertEqual((to_store["order"]["id"], to_store["order"]["status"]), (order["id"], "received"))
        self.assertIsNone(to_store["order"]["delivery_pin"])

        self.assertTrue(await stranger.receive_nothing())
        await self.close_all()

    async def test_captains_see_orders_appear_and_disappear(self):
        order = await self.place_order()
        customer, _, _ = await self.connect(self.customer)
        captain, _, _ = await self.connect(self.captain)
        # Nothing for captains until the store accepts.
        self.assertTrue(await captain.receive_nothing())

        await self.api(self.owner, "post", f"/api/orders/{order['id']}/accept/", {"prep_minutes": 15})
        self.assertEqual((await customer.receive_json_from())["order"]["status"], "preparing")
        available = await captain.receive_json_from()
        self.assertEqual((available["type"], available["order"]["id"]), ("order.available", order["id"]))
        self.assertIsNone(available["order"]["delivery_pin"])

        await self.api(self.captain, "post", f"/api/orders/{order['id']}/claim/")
        messages = [await captain.receive_json_from(), await captain.receive_json_from()]
        types = sorted(message["type"] for message in messages)
        # The captain gets their own order update and the "gone from the list" notice.
        self.assertEqual(types, ["order.unavailable", "order.updated"])
        self.assertEqual((await customer.receive_json_from())["order"]["captain"], self.captain.pk)
        await self.close_all()
