from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from vendors.models import Vendor

from .models import Order

BAGHDAD = Point(44.4009, 33.3406, srid=4326)


class OrderApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000010")
        self.other_customer = User.objects.create_user(phone="+9647700000011")
        self.captain = User.objects.create_user(phone="+9647700000012", role=User.Role.CAPTAIN)
        self.owner = User.objects.create_user(phone="+9647700000013", role=User.Role.VENDOR)
        vendor = Vendor.objects.create(owner=self.owner, name="Kebab", location=BAGHDAD)

        self.order = Order.objects.create(
            customer=self.customer,
            vendor=vendor,
            captain=self.captain,
            delivery_address="Karrada, street 52",
            delivery_location=BAGHDAD,
            subtotal=10000,
            delivery_fee=2000,
            service_fee=500,
            discount=1000,
            tip=1000,
        )
        self.client = APIClient()

    def order_ids(self, user):
        self.client.force_authenticate(user)
        return [order["id"] for order in self.client.get("/api/orders/").json()["results"]]

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/orders/").status_code, 401)

    def test_customer_captain_and_vendor_owner_see_the_order(self):
        for user in (self.customer, self.captain, self.owner):
            with self.subTest(user=user.role):
                self.assertEqual(self.order_ids(user), [self.order.pk])

    def test_other_customers_do_not(self):
        self.assertEqual(self.order_ids(self.other_customer), [])

    def test_calculate_total(self):
        self.assertEqual(self.order.calculate_total(), 12500)
