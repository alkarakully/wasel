from datetime import timedelta
from unittest import mock

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Point
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from vendors.models import Vendor
from wasel.asgi import application

from .models import CaptainLocation, Order
from .tracking import update_captain_location

STORE = Point(44.4009, 33.3406, srid=4326)
HOME = Point(44.4009, 33.3496, srid=4326)


class TrackingSetup:
    def make_people(self):
        self.customer = User.objects.create_user(phone="+9647700000080")
        self.owner = User.objects.create_user(phone="+9647800000081", role=User.Role.VENDOR)
        self.captain = User.objects.create_user(phone="+9647500000082", role=User.Role.CAPTAIN)
        self.vendor = Vendor.objects.create(owner=self.owner, name="Map Grill", location=STORE, is_open=True)

    def make_order(self, **fields):
        fields.setdefault("captain", self.captain)
        fields.setdefault("status", Order.Status.OUT_FOR_DELIVERY)
        return Order.objects.create(
            customer=self.customer, vendor=self.vendor, delivery_address="Karrada", delivery_location=HOME, **fields
        )


@mock.patch("orders.tracking.realtime.send_captain_location")
class UpdateLocationTests(TrackingSetup, TestCase):
    def setUp(self):
        self.make_people()

    def test_saves_latest_position_and_sends_to_active_orders_only(self, send):
        active = self.make_order()
        self.make_order(status=Order.Status.DELIVERED)
        self.assertTrue(update_captain_location(self.captain, 33.345, 44.401, heading=90, speed=6.5))

        location = CaptainLocation.objects.get(captain=self.captain)
        self.assertEqual((round(location.point.y, 3), round(location.point.x, 3)), (33.345, 44.401))
        send.assert_called_once()
        order_id, customer_id, vendor_id, payload = send.call_args.args
        self.assertEqual((order_id, customer_id, vendor_id), (active.pk, self.customer.pk, self.vendor.pk))
        self.assertEqual((payload["lat"], payload["heading"], payload["speed"]), (33.345, 90, 6.5))

    def test_updates_within_two_seconds_are_dropped(self, send):
        self.make_order()
        self.assertTrue(update_captain_location(self.captain, 33.345, 44.401))
        self.assertFalse(update_captain_location(self.captain, 33.346, 44.401))
        self.assertEqual(send.call_count, 1)
        CaptainLocation.objects.update(updated_at=timezone.now() - timedelta(seconds=3))
        self.assertTrue(update_captain_location(self.captain, 33.347, 44.401))
        self.assertEqual(CaptainLocation.objects.count(), 1)


@mock.patch("orders.tracking.realtime.send_captain_location")
class LocationApiTests(TrackingSetup, TestCase):
    def setUp(self):
        self.make_people()
        self.client = APIClient()

    def post(self, user, body):
        self.client.force_authenticate(user)
        return self.client.post("/api/captain/location/", body, format="json")

    def test_captain_posts_location(self, send):
        self.assertEqual(self.post(self.captain, {"lat": 33.345, "lng": 44.401}).status_code, 204)
        self.assertTrue(CaptainLocation.objects.filter(captain=self.captain).exists())

    def test_only_captains(self, send):
        self.assertEqual(self.post(self.customer, {"lat": 33.345, "lng": 44.401}).status_code, 403)

    def test_bad_coordinates(self, send):
        self.assertEqual(self.post(self.captain, {"lat": 95, "lng": 44.401}).status_code, 400)

    def test_order_shows_captain_location_only_while_active(self, send):
        order = self.make_order()
        update_captain_location(self.captain, 33.345, 44.401)
        self.client.force_authenticate(self.customer)
        body = self.client.get(f"/api/orders/{order.pk}/").json()
        self.assertEqual(body["vendor_name"], "Map Grill")
        self.assertEqual(body["delivery_location"], {"lat": HOME.y, "lng": HOME.x})
        self.assertAlmostEqual(body["captain_location"]["lat"], 33.345)

        Order.objects.filter(pk=order.pk).update(status=Order.Status.DELIVERED)
        self.assertIsNone(self.client.get(f"/api/orders/{order.pk}/").json()["captain_location"])

    def test_tracking_page_renders(self, send):
        response = self.client.get("/track/42/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "window.WASEL_ORDER_ID = 42;")


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class LocationSocketTests(TrackingSetup, TransactionTestCase):
    def setUp(self):
        self.make_people()
        self.stranger = User.objects.create_user(phone="+9647700000083")
        self.order = self.make_order()
        self.tokens = {u.pk: Token.objects.create(user=u).key for u in (self.customer, self.owner, self.captain, self.stranger)}

    async def connect(self, user):
        socket = WebsocketCommunicator(application, f"/ws/orders/?token={self.tokens[user.pk]}")
        await socket.connect()
        await socket.receive_json_from()  # "connected"
        return socket

    async def test_captain_position_reaches_customer_and_store(self):
        captain = await self.connect(self.captain)
        customer = await self.connect(self.customer)
        store = await self.connect(self.owner)
        stranger = await self.connect(self.stranger)

        await captain.send_json_to({"type": "location", "lat": 33.3451, "lng": 44.4009, "heading": 0})

        for socket in (customer, store):
            message = await socket.receive_json_from()
            self.assertEqual((message["type"], message["order_id"]), ("captain.location", self.order.pk))
            self.assertAlmostEqual(message["location"]["lat"], 33.3451)
        self.assertTrue(await stranger.receive_nothing())
        saved = await database_sync_to_async(CaptainLocation.objects.get)(captain=self.captain)
        self.assertAlmostEqual(saved.point.y, 33.3451)

        for socket in (captain, customer, store, stranger):
            await socket.disconnect()

    async def test_customers_cannot_send_locations(self):
        customer = await self.connect(self.customer)
        await customer.send_json_to({"type": "location", "lat": 33.3, "lng": 44.4})
        self.assertEqual((await customer.receive_json_from())["error"], "not_allowed")
        await customer.disconnect()

    async def test_invalid_location_is_reported(self):
        captain = await self.connect(self.captain)
        await captain.send_json_to({"type": "location", "lat": "north"})
        self.assertEqual((await captain.receive_json_from())["error"], "invalid_location")
        await captain.disconnect()
