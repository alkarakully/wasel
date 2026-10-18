"""
Tenant isolation: nobody at one store can see or change another store's
orders, menu, hours, team, reports or billing, and live sockets follow
access changes at once. Every store-facing endpoint is tried from every role
at store A against store B.
"""

from datetime import date, timedelta
from decimal import Decimal

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.gis.geos import Point
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import Statement
from orders.models import Order, OrderItem
from wasel.asgi import application

from .models import Product, StoreMember, Vendor

BAGHDAD = Point(44.4214, 33.3045, srid=4326)
IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def make_store(name, owner_phone):
    owner = User.objects.create_user(owner_phone, role=User.Role.VENDOR, name=f"{name} owner")
    store = Vendor.objects.create(owner=owner, name=name, location=BAGHDAD, is_open=True, commission_rate=Decimal("15"))
    product = Product.objects.create(vendor=store, name_ar="كباب", name_en="Kebab", price=9000)
    return owner, store, product


def make_order(store, product, customer, status=Order.Status.RECEIVED):
    order = Order.objects.create(
        customer=customer,
        vendor=store,
        status=status,
        delivery_address="Karrada",
        delivery_location=BAGHDAD,
        subtotal=9000,
        commission_amount=1350,
        total_amount=11000,
        delivered_at=timezone.now() if status == Order.Status.DELIVERED else None,
    )
    OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=9000, line_total=9000)
    return order


class CrossStoreTests(TestCase):
    def setUp(self):
        self.owner_a, self.store_a, self.product_a = make_store("Store A", "+9647800000301")
        self.owner_b, self.store_b, self.product_b = make_store("Store B", "+9647800000302")
        self.manager_a = User.objects.create_user("+9647800000303", role=User.Role.VENDOR)
        self.cashier_a = User.objects.create_user("+9647800000304", role=User.Role.VENDOR)
        StoreMember.objects.create(vendor=self.store_a, user=self.manager_a, role="manager")
        StoreMember.objects.create(vendor=self.store_a, user=self.cashier_a, role="cashier")
        self.member_b = User.objects.create_user("+9647800000305", role=User.Role.VENDOR)
        self.membership_b = StoreMember.objects.create(vendor=self.store_b, user=self.member_b, role="cashier")

        self.customer = User.objects.create_user("+9647700000306", name="Zainab")
        self.order_a = make_order(self.store_a, self.product_a, self.customer)
        self.order_b = make_order(self.store_b, self.product_b, self.customer)
        start = date(2026, 10, 10)
        self.statement_b = Statement.objects.create(
            vendor=self.store_b, period_start=start, period_end=start + timedelta(days=6), orders_count=1, payout=7650
        )
        self.everyone_at_a = [self.owner_a, self.manager_a, self.cashier_a]

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def assert_denied(self, response, label):
        self.assertIn(response.status_code, (403, 404), f"{label}: got {response.status_code} {response.content[:200]}")

    def test_store_a_cannot_touch_store_b(self):
        b, prod_b, order_b = self.store_b.pk, self.product_b.pk, self.order_b.pk
        attempts = [
            ("team list", "get", f"/api/vendors/{b}/team/", None),
            ("team add", "post", f"/api/vendors/{b}/team/", {"phone": "07800000399", "role": "manager"}),
            ("member role", "patch", f"/api/vendors/{b}/team/{self.membership_b.pk}/", {"role": "manager"}),
            ("member remove", "delete", f"/api/vendors/{b}/team/{self.membership_b.pk}/", None),
            ("add item", "post", f"/api/vendors/{b}/products/", {"name_ar": "x", "price": "1000"}),
            ("edit item", "patch", f"/api/products/{prod_b}/", {"price": "1"}),
            ("remove item", "delete", f"/api/products/{prod_b}/", None),
            ("stock", "post", f"/api/products/{prod_b}/availability/", {"is_available": False}),
            ("hours", "put", f"/api/vendors/{b}/hours/", {"sat": None}),
            ("open/close", "post", f"/api/vendors/{b}/open/", {"is_open": False}),
            ("report", "get", f"/api/vendors/{b}/report/", None),
            ("billing", "get", f"/api/vendors/{b}/billing/", None),
            ("statement", "get", f"/api/vendors/{b}/statements/{self.statement_b.pk}/", None),
            ("statement csv", "get", f"/api/vendors/{b}/statements/{self.statement_b.pk}/?download=csv", None),
            ("order detail", "get", f"/api/orders/{order_b}/", None),
            ("accept", "post", f"/api/orders/{order_b}/accept/", {"prep_minutes": 15}),
            ("reject", "post", f"/api/orders/{order_b}/reject/", {"reason": "x"}),
            ("ready", "post", f"/api/orders/{order_b}/ready/", None),
        ]
        for user in self.everyone_at_a:
            client = self.client_for(user)
            for label, method, path, body in attempts:
                response = getattr(client, method)(path, body, format="json") if body is not None else getattr(client, method)(path)
                self.assert_denied(response, f"{user.phone} {label}")

        # Nothing changed at store B.
        self.store_b.refresh_from_db()
        self.product_b.refresh_from_db()
        self.order_b.refresh_from_db()
        self.membership_b.refresh_from_db()
        self.assertTrue(self.store_b.is_open)
        self.assertEqual((self.product_b.price, self.product_b.is_available), (Decimal("9000"), True))
        self.assertEqual(self.order_b.status, Order.Status.RECEIVED)
        self.assertEqual(self.membership_b.role, "cashier")
        self.assertEqual(self.store_b.products.count(), 1)
        self.assertEqual(self.store_b.members.count(), 1)

    def test_lists_only_show_your_own_store(self):
        for user in self.everyone_at_a:
            client = self.client_for(user)
            orders = client.get("/api/orders/?status=received,preparing,ready").data["results"]
            self.assertEqual([o["id"] for o in orders], [self.order_a.pk], user.phone)
            stores = client.get("/api/vendors/mine/").data
            self.assertEqual([s["id"] for s in stores], [self.store_a.pk], user.phone)

    def test_a_statement_id_from_another_store_is_not_found_through_your_own(self):
        response = self.client_for(self.owner_a).get(
            f"/api/vendors/{self.store_a.pk}/statements/{self.statement_b.pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_customer_details_stay_with_the_order_s_store(self):
        own = self.client_for(self.owner_a).get(f"/api/orders/{self.order_a.pk}/").data
        self.assertEqual(own["customer_contact"]["name"], "Zainab")
        self.assertIsNone(own["delivery_pin"])

    def test_customers_captains_and_strangers_get_no_store_admin(self):
        captain = User.objects.create_user("+9647500000307", role=User.Role.CAPTAIN)
        for user in (self.customer, captain):
            client = self.client_for(user)
            for path in (
                f"/api/vendors/{self.store_a.pk}/team/",
                f"/api/vendors/{self.store_a.pk}/report/",
                f"/api/vendors/{self.store_a.pk}/billing/",
            ):
                self.assert_denied(client.get(path), f"{user.phone} {path}")
            self.assertEqual(client.get("/api/vendors/mine/").data, [])

    def test_ops_is_staff_only(self):
        for user in (self.owner_a, self.customer):
            client = APIClient()
            client.force_login(user)
            for path in ("/api/ops/overview/", "/api/ops/orders/", "/api/ops/users/", "/api/ops/payouts/"):
                self.assertEqual(client.get(path).status_code, 403, f"{user.phone} {path}")

    def test_blocked_accounts_lose_api_access(self):
        token = Token.objects.create(user=self.cashier_a)
        self.cashier_a.is_active = False
        self.cashier_a.save()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(client.get("/api/vendors/mine/").status_code, 401)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class SocketIsolationTests(TransactionTestCase):
    def setUp(self):
        self.owner_a, self.store_a, self.product_a = make_store("Store A", "+9647800000401")
        self.owner_b, self.store_b, self.product_b = make_store("Store B", "+9647800000402")
        self.cashier = User.objects.create_user("+9647800000403", role=User.Role.VENDOR)
        self.membership = StoreMember.objects.create(vendor=self.store_a, user=self.cashier, role="cashier")
        self.customer = User.objects.create_user("+9647700000404")
        self.sockets = []

    async def connect(self, user):
        token = await database_sync_to_async(lambda: Token.objects.get_or_create(user=user)[0].key)()
        socket = WebsocketCommunicator(application, f"/ws/orders/?token={token}")
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        self.sockets.append(socket)
        first = await socket.receive_json_from()
        return socket, first

    async def close_all(self):
        for socket in self.sockets:
            await socket.disconnect()

    @database_sync_to_async
    def place_order(self, store, product):
        client = APIClient()
        client.force_authenticate(self.customer)
        response = client.post(
            "/api/orders/",
            {
                "vendor": store.pk,
                "items": [{"product": product.pk, "quantity": "1"}],
                "delivery_latitude": 33.3045,
                "delivery_longitude": 44.4214,
                "delivery_address": "Karrada",
                "payment_type": "cod",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        return response.json()["id"]

    async def test_a_store_only_hears_its_own_orders(self):
        owner_b, _ = await self.connect(self.owner_b)
        cashier_a, _ = await self.connect(self.cashier)

        order_a = await self.place_order(self.store_a, self.product_a)
        event = await cashier_a.receive_json_from(timeout=2)
        self.assertEqual(event["order"]["id"], order_a)
        self.assertTrue(await owner_b.receive_nothing(timeout=0.3))
        await self.close_all()

    async def test_removed_staff_are_cut_off_at_once(self):
        cashier, _ = await self.connect(self.cashier)
        await database_sync_to_async(self.membership.delete)()

        closed = await cashier.receive_output(timeout=2)
        self.assertEqual(closed, {"type": "websocket.close", "code": 4409})

        # Reconnecting no longer joins store A.
        again, _ = await self.connect(self.cashier)
        await self.place_order(self.store_a, self.product_a)
        self.assertTrue(await again.receive_nothing(timeout=0.3))
        await self.close_all()

    async def test_blocked_users_are_refused_on_reconnect(self):
        cashier, _ = await self.connect(self.cashier)

        def block():
            self.cashier.is_active = False
            self.cashier.save()

        await database_sync_to_async(block)()
        closed = await cashier.receive_output(timeout=2)
        self.assertEqual(closed["code"], 4409)

        token = await database_sync_to_async(lambda: Token.objects.get(user=self.cashier).key)()
        retry = WebsocketCommunicator(application, f"/ws/orders/?token={token}")
        await retry.connect()
        self.assertEqual(await retry.receive_output(timeout=2), {"type": "websocket.close", "code": 4401})
        await retry.disconnect()
        await self.close_all()

    async def test_signing_out_closes_open_sockets(self):
        owner, _ = await self.connect(self.owner_a)
        await database_sync_to_async(lambda: Token.objects.filter(user=self.owner_a).delete())()
        closed = await owner.receive_output(timeout=2)
        self.assertEqual(closed["code"], 4409)
        await self.close_all()
