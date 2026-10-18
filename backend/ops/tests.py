from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from orders.models import CaptainLocation, Order, StuckOrderAlert
from vendors.models import Vendor

BAGHDAD = Point(44.4214, 33.3045, srid=4326)


class OpsTestCase(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser("+9647700000990", "a-strong-admin-pass", name="Ops")
        self.customer = User.objects.create_user("+9647700000991", name="Zainab")
        self.captain = User.objects.create_user("+9647500000992", role=User.Role.CAPTAIN, name="Ali")
        owner = User.objects.create_user("+9647800000993", role=User.Role.VENDOR)
        self.store = Vendor.objects.create(
            owner=owner, name="Tigris Grill", location=BAGHDAD, is_open=True, commission_rate=Decimal("15")
        )
        self.client.force_login(self.staff)

    def order(self, status=Order.Status.RECEIVED, total=10000, commission=1500, **extra):
        return Order.objects.create(
            customer=self.customer,
            vendor=self.store,
            status=status,
            delivery_address="Karrada",
            delivery_location=BAGHDAD,
            total_amount=total,
            commission_amount=commission,
            service_fee=500,
            delivery_fee=1500,
            **extra,
        )


class AccessTests(OpsTestCase):
    def test_only_staff_get_in(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/api/ops/overview/").status_code, 403)
        self.assertEqual(self.client.get("/ops/").status_code, 302)

    def test_app_tokens_dont_open_ops(self):
        """Staff use the admin session; a phone app's token is not enough."""
        from rest_framework.authtoken.models import Token

        self.client.logout()
        token = Token.objects.create(user=self.staff)
        response = self.client.get("/api/ops/overview/", HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertIn(response.status_code, (401, 403))

    def test_page_loads_for_staff(self):
        response = self.client.get("/ops/")
        self.assertContains(response, "ops/ops.js")


class OverviewTests(OpsTestCase):
    def test_todays_numbers_skip_cancelled_orders(self):
        self.order(Order.Status.DELIVERED, delivered_at=timezone.now())
        self.order(Order.Status.PREPARING)
        self.order(Order.Status.CANCELLED, total=99999, commission=9999)
        CaptainLocation.objects.create(captain=self.captain, point=BAGHDAD, is_online=True, updated_at=timezone.now())

        data = self.client.get("/api/ops/overview/").json()
        self.assertEqual(data["today"]["orders"], 3)
        self.assertEqual(data["today"]["delivered"], 1)
        self.assertEqual(data["today"]["cancelled"], 1)
        self.assertEqual(data["today"]["sales"], 20000)
        self.assertEqual(data["today"]["commission"], 3000)
        self.assertEqual(data["live"]["active_orders"], 1)
        self.assertEqual(data["live"]["online_captains"], 1)
        self.assertEqual(data["by_status"]["preparing"], 1)
        self.assertEqual(data["top_stores"][0]["name"], "Tigris Grill")


class OrdersAndAlertsTests(OpsTestCase):
    def test_live_orders_show_open_alerts(self):
        stuck = self.order()
        self.order(Order.Status.DELIVERED)
        StuckOrderAlert.objects.create(order=stuck, reason=StuckOrderAlert.Reason.NOT_ACCEPTED)

        orders = self.client.get("/api/ops/orders/").json()
        self.assertEqual([o["id"] for o in orders], [stuck.pk])
        self.assertEqual(orders[0]["alerts"], ["not_accepted"])

    def test_staff_resolve_an_alert(self):
        alert = StuckOrderAlert.objects.create(order=self.order(), reason=StuckOrderAlert.Reason.NOT_ACCEPTED)
        self.assertEqual(len(self.client.get("/api/ops/alerts/").json()), 1)

        self.client.post(f"/api/ops/alerts/{alert.pk}/resolve/", content_type="application/json")
        alert.refresh_from_db()
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(self.client.get("/api/ops/alerts/").json(), [])


class CaptainsTests(OpsTestCase):
    def test_online_captains_with_where_they_are_and_what_they_carry(self):
        order = self.order(Order.Status.OUT_FOR_DELIVERY, captain=self.captain)
        CaptainLocation.objects.create(captain=self.captain, point=BAGHDAD, is_online=True, updated_at=timezone.now())
        stale = User.objects.create_user("+9647500000994", role=User.Role.CAPTAIN)
        CaptainLocation.objects.create(
            captain=stale, point=BAGHDAD, is_online=False, updated_at=timezone.now() - timedelta(days=3)
        )

        captains = self.client.get("/api/ops/captains/").json()
        self.assertEqual(len(captains), 1)
        self.assertEqual(captains[0]["order"], order.pk)
        self.assertAlmostEqual(captains[0]["lat"], 33.3045)


class StoresAndUsersTests(OpsTestCase):
    def test_stores_with_todays_sales_and_open_switch(self):
        self.order(Order.Status.DELIVERED)
        stores = self.client.get("/api/ops/stores/").json()
        self.assertEqual(stores[0]["orders_today"], 1)
        self.assertEqual(stores[0]["sales_today"], 10000)
        self.assertEqual(stores[0]["commission_rate"], "15")

        self.client.post(f"/api/ops/stores/{self.store.pk}/open/", {"is_open": False}, content_type="application/json")
        self.store.refresh_from_db()
        self.assertFalse(self.store.is_open)

    def test_accounts_filter_search_and_block(self):
        data = self.client.get("/api/ops/users/?role=captain").json()
        self.assertEqual([u["phone"] for u in data["results"]], ["+9647500000992"])
        self.assertEqual(data["counts"]["vendor"], 1)

        found = self.client.get("/api/ops/users/?q=0770 000 0991".replace(" ", "")).json()["results"]
        self.assertEqual([u["name"] for u in found], ["Zainab"])

        self.client.post(f"/api/ops/users/{self.captain.pk}/active/", {"is_active": False}, content_type="application/json")
        self.captain.refresh_from_db()
        self.assertFalse(self.captain.is_active)

    def test_staff_accounts_are_left_to_the_admin(self):
        response = self.client.post(
            f"/api/ops/users/{self.staff.pk}/active/", {"is_active": False}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
