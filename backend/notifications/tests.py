from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from orders.models import CaptainLocation, Order
from vendors.models import Vendor

from . import push
from .models import Device
from .tasks import send_push


class RecordingSender:
    sent = []
    invalid = set()

    def send(self, fid, message):
        if fid in self.invalid:
            return push.INVALID_TOKEN
        self.sent.append((fid, message))
        return push.OK


TEST_PUSH = {"SENDER": "notifications.tests.RecordingSender", "FCM_CREDENTIALS_FILE": "", "FCM_PROJECT_ID": ""}


@override_settings(PUSH=TEST_PUSH)
class PushTestCase(TestCase):
    def setUp(self):
        push._sender = None  # pick up the test sender
        RecordingSender.sent, RecordingSender.invalid = [], set()
        self.customer = User.objects.create_user(phone="+9647700000500", language_pref="en")
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def tearDown(self):
        push._sender = None


class DeviceApiTests(PushTestCase):
    def test_register_update_and_remove(self):
        body = {"fid": "tok-1", "platform": "ios", "app": "customer"}
        self.assertEqual(self.client.post("/api/devices/", body, format="json").status_code, 204)
        self.client.post("/api/devices/", body, format="json")  # registering twice is fine
        self.assertEqual(Device.objects.count(), 1)

        # Same phone, different account: the token moves.
        other = User.objects.create_user(phone="+9647700000501")
        self.client.force_authenticate(other)
        self.client.post("/api/devices/", body, format="json")
        self.assertEqual(Device.objects.get().user, other)

        self.client.delete("/api/devices/", {"fid": "tok-1"}, format="json")
        self.assertFalse(Device.objects.exists())

    def test_validates_platform_and_app(self):
        response = self.client.post("/api/devices/", {"fid": "t", "platform": "nokia", "app": "customer"}, format="json")
        self.assertEqual(response.status_code, 400)


class SendPushTests(PushTestCase):
    def test_sends_in_users_language_to_that_apps_devices(self):
        Device.objects.create(user=self.customer, fid="phone", platform="ios", app="customer")
        Device.objects.create(user=self.customer, fid="captain-phone", platform="ios", app="captain")
        self.assertEqual(send_push(self.customer.pk, "customer", "order_delivered", {"order_id": 7, "store": "Tigris Grill"}), 1)

        token, message = RecordingSender.sent[0]
        self.assertEqual(token, "phone")
        self.assertEqual((message.title, message.body), ("Delivered. Enjoy!", "Thanks for ordering from Tigris Grill."))
        self.assertEqual(message.data, {"kind": "order_delivered", "order_id": 7})

    def test_arabic_users_get_arabic(self):
        User.objects.filter(pk=self.customer.pk).update(language_pref="ar")
        Device.objects.create(user=self.customer, fid="phone", platform="android", app="customer")
        send_push(self.customer.pk, "customer", "order_out_for_delivery", {"order_id": 7, "store": "x"})
        self.assertEqual(RecordingSender.sent[0][1].title, "الكابتن في الطريق إليك")

    def test_offers_are_urgent_and_short_lived(self):
        Device.objects.create(user=self.customer, fid="phone", platform="ios", app="captain")
        send_push(self.customer.pk, "captain", "offer", {"offer_id": 3, "order_id": 7, "store": "Grill", "km": "0.5", "seconds": 30})
        message = RecordingSender.sent[0][1]
        self.assertTrue(message.urgent)
        self.assertEqual(message.ttl_seconds, 30)
        self.assertEqual(message.body, "Grill is 0.5 km away. You have 30 seconds to accept.")

    def test_dead_tokens_are_forgotten(self):
        Device.objects.create(user=self.customer, fid="gone", platform="ios", app="customer")
        RecordingSender.invalid = {"gone"}
        send_push(self.customer.pk, "customer", "order_delivered", {"order_id": 7, "store": "x"})
        self.assertFalse(Device.objects.exists())


class FcmSenderTests(TestCase):
    def sender(self, response):
        sender = object.__new__(push.FcmSender)  # skip loading credentials
        sender.project_id = "wasel-test"
        sender.session = mock.Mock(post=mock.Mock(return_value=response))
        return sender

    def test_message_format(self):
        message = self.sender(None).message("tok", push.Push("T", "B", {"order_id": 7}, ttl_seconds=30, urgent=True))["message"]
        self.assertEqual(message["fid"], "tok")
        self.assertEqual(message["notification"], {"title": "T", "body": "B"})
        self.assertEqual(message["data"], {"order_id": "7"})
        self.assertEqual((message["android"]["priority"], message["android"]["ttl"]), ("high", "30s"))
        self.assertEqual(message["apns"]["headers"]["apns-priority"], "10")
        self.assertIn("apns-expiration", message["apns"]["headers"])

    def test_posts_to_project_and_reads_results(self):
        ok = mock.Mock(status_code=200, content=b"{}")
        sender = self.sender(ok)
        self.assertEqual(sender.send("tok", push.Push("T", "B")), push.OK)
        self.assertEqual(sender.session.post.call_args.args[0], "https://fcm.googleapis.com/v1/projects/wasel-test/messages:send")

        gone = mock.Mock(status_code=404, content=b"x", json=lambda: {"error": {"details": [{"errorCode": "UNREGISTERED"}]}})
        self.assertEqual(self.sender(gone).send("tok", push.Push("T", "B")), push.INVALID_TOKEN)

        down = mock.Mock(status_code=503, content=b"x", json=lambda: {"error": {"message": "busy"}})
        with self.assertRaises(push.PushError):
            self.sender(down).send("tok", push.Push("T", "B"))


@mock.patch("orders.realtime._send")
class OrderFlowPushTests(PushTestCase):
    def setUp(self):
        super().setUp()
        owner = User.objects.create_user(phone="+9647800000502", role=User.Role.VENDOR)
        self.owner = owner
        store = Vendor.objects.create(owner=owner, name="Tigris Grill", location=Point(44.4009, 33.3406, srid=4326), is_open=True)
        self.order = Order.objects.create(
            customer=self.customer, vendor=store, delivery_address="Karrada", delivery_location=Point(44.4009, 33.3496, srid=4326)
        )
        Device.objects.create(user=self.customer, fid="customer-phone", platform="ios", app="customer")

    def test_store_accepting_tells_the_customer(self, send):
        self.client.force_authenticate(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"/api/orders/{self.order.pk}/accept/", {"prep_minutes": 20}, format="json")
        titles = [m.title for _, m in RecordingSender.sent]
        self.assertIn("Tigris Grill accepted your order", titles)
        self.assertEqual(RecordingSender.sent[-1][1].body, "It'll be ready in about 20 minutes.")

    def test_rejection_tells_the_customer_why(self, send):
        self.client.force_authenticate(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"/api/orders/{self.order.pk}/reject/", {"reason": "Out of bread"}, format="json")
        token, message = RecordingSender.sent[-1]
        self.assertEqual((message.title, message.body), ("Your order from Tigris Grill was cancelled", "Out of bread"))

    def test_dispatch_offer_reaches_captains_phone(self, send):
        captain = User.objects.create_user(phone="+9647500000503", role=User.Role.CAPTAIN, language_pref="en")
        CaptainLocation.objects.create(
            captain=captain, point=Point(44.4009, 33.3410, srid=4326), is_online=True, updated_at=timezone.now()
        )
        Device.objects.create(user=captain, fid="captain-phone", platform="ios", app="captain")
        self.client.force_authenticate(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f"/api/orders/{self.order.pk}/accept/", {"prep_minutes": 15}, format="json")

        to_captain = [m for token, m in RecordingSender.sent if token == "captain-phone"]
        self.assertEqual(len(to_captain), 1)
        self.assertEqual(to_captain[0].title, "New order for you")
        self.assertEqual(to_captain[0].data["order_id"], self.order.pk)
        self.assertIn("offer_id", to_captain[0].data)
