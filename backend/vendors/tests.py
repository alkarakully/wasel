from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User

from .models import Offer, Product, ProductModifier, Vendor

# Baghdad, Tahrir Square
TAHRIR = (33.3406, 44.4009)


def make_vendor(owner, name, lat, lng, **kwargs):
    return Vendor.objects.create(owner=owner, name=name, location=Point(lng, lat, srid=4326), **kwargs)


class CommissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="+9647700000001", role=User.Role.VENDOR)

    def test_commission_is_percent_of_subtotal_rounded_to_dinar(self):
        vendor = make_vendor(self.owner, "Kebab", *TAHRIR, commission_rate=Decimal("17.5"))
        self.assertEqual(vendor.commission_for(10_250), Decimal(1794))

    def test_no_commission_during_free_period(self):
        vendor = make_vendor(
            self.owner,
            "Kebab",
            *TAHRIR,
            commission_free_until=timezone.now() + timedelta(days=30),
        )
        self.assertEqual(vendor.commission_for(20_000), Decimal(0))

    def test_commission_resumes_after_free_period(self):
        vendor = make_vendor(
            self.owner,
            "Kebab",
            *TAHRIR,
            commission_free_until=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(vendor.commission_for(20_000), Decimal(3000))


class VendorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(phone="+9647700000002", role=User.Role.VENDOR)
        # ~1 km from Tahrir, open
        self.near_open = make_vendor(owner, "Near Open", 33.3496, 44.4009, is_open=True, cuisine="eastern")
        # ~0.5 km from Tahrir, closed
        self.near_closed = make_vendor(owner, "Near Closed", 33.3451, 44.4009, is_open=False)
        # Basra: far outside any delivery radius
        self.far = make_vendor(owner, "Basra Grill", 30.5085, 47.7804, is_open=True)

        product = Product.objects.create(vendor=self.near_open, name_ar="تكة", price=8000)
        ProductModifier.objects.create(product=product, group_name="Extras", name_ar="صمون", price_delta=500)

    def names(self, response):
        return [vendor["name"] for vendor in response.json()["results"]]

    def test_location_filter_hides_far_vendors_and_puts_open_first(self):
        response = self.client.get("/api/vendors/", {"lat": TAHRIR[0], "lng": TAHRIR[1]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Near Open", "Near Closed"])

    def test_location_list_includes_distance_and_delivery_fee(self):
        response = self.client.get("/api/vendors/", {"lat": TAHRIR[0], "lng": TAHRIR[1]})
        near_open = response.json()["results"][0]
        self.assertAlmostEqual(near_open["distance_km"], 1.0, delta=0.05)
        self.assertEqual(near_open["delivery_fee"], "1500")
        self.assertIsNone(self.client.get("/api/vendors/").json()["results"][0]["delivery_fee"])

    def test_cuisine_filter(self):
        response = self.client.get("/api/vendors/", {"cuisine": "eastern"})
        self.assertEqual(self.names(response), ["Near Open"])

    def test_bad_coordinates_return_400(self):
        response = self.client.get("/api/vendors/", {"lat": "abc", "lng": "44"})
        self.assertEqual(response.status_code, 400)

    def test_detail_includes_menu_with_modifiers(self):
        response = self.client.get(f"/api/vendors/{self.near_open.pk}/")
        products = response.json()["products"]
        self.assertEqual(products[0]["name_ar"], "تكة")
        self.assertEqual(products[0]["modifiers"][0]["name_ar"], "صمون")

    def test_only_running_offers_are_listed(self):
        now = timezone.now()
        Offer.objects.create(title="Live", type="percent", value=10, starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1))
        Offer.objects.create(title="Ended", type="percent", value=10, starts_at=now - timedelta(days=5), ends_at=now - timedelta(days=1))
        response = self.client.get("/api/offers/")
        self.assertEqual([offer["title"] for offer in response.json()["results"]], ["Live"])


class StoreOwnerApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="+9647800000030", role=User.Role.VENDOR)
        self.other_owner = User.objects.create_user(phone="+9647800000031", role=User.Role.VENDOR)
        self.store = make_vendor(self.owner, "Owner Grill", *TAHRIR, is_open=True)
        make_vendor(self.other_owner, "Someone Else", *TAHRIR)
        self.product = Product.objects.create(vendor=self.store, name_ar="تكة", price=8000)
        self.client = APIClient()

    def test_mine_lists_only_my_stores_with_menus(self):
        self.client.force_authenticate(self.owner)
        stores = self.client.get("/api/vendors/mine/").json()
        self.assertEqual([s["name"] for s in stores], ["Owner Grill"])
        self.assertEqual(stores[0]["products"][0]["name_ar"], "تكة")

    def test_mine_needs_login(self):
        self.assertEqual(self.client.get("/api/vendors/mine/").status_code, 401)

    def test_owner_opens_and_closes_store(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/vendors/{self.store.pk}/open/", {"is_open": False}, format="json")
        self.assertEqual(response.json(), {"id": self.store.pk, "is_open": False})
        self.store.refresh_from_db()
        self.assertFalse(self.store.is_open)

    def test_other_owner_cannot_close_my_store(self):
        self.client.force_authenticate(self.other_owner)
        response = self.client.post(f"/api/vendors/{self.store.pk}/open/", {"is_open": False}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_open_needs_a_boolean(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(f"/api/vendors/{self.store.pk}/open/", {}, format="json").status_code, 400)

    def test_owner_marks_item_out_of_stock(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/products/{self.product.pk}/availability/", {"is_available": False}, format="json")
        self.assertEqual(response.json(), {"id": self.product.pk, "is_available": False})
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_available)

    def test_other_owner_cannot_change_my_items(self):
        self.client.force_authenticate(self.other_owner)
        response = self.client.post(f"/api/products/{self.product.pk}/availability/", {"is_available": False}, format="json")
        self.assertEqual(response.status_code, 403)
