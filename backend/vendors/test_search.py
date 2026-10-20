from datetime import timedelta

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User

from .models import Offer, Product, Vendor
from .search import fold

KARRADA = {"lat": "33.305", "lng": "44.42"}


def store(owner, name, kind="restaurant", cuisine="", lng=44.42, **kwargs):
    return Vendor.objects.create(
        status=Vendor.Status.APPROVED, owner=owner, name=name, type=kind, cuisine=cuisine,
        location=Point(lng, 33.305, srid=4326), is_open=True, **kwargs,
    )


class SearchTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(phone="+9647800000080", role=User.Role.VENDOR)
        self.grill = store(owner, "مطعم دجلة للمشويات", cuisine="eastern")
        self.burger = store(owner, "برغر الكرادة", cuisine="fast_food", lng=44.43)
        self.pharmacy = store(owner, "صيدلية الشفاء", kind="pharmacy")
        self.flowers = store(owner, "Karrada Flowers", kind="flowers")
        Product.objects.create(vendor=self.grill, name_ar="كباب عراقي", name_en="Iraqi kebab", price=9000)
        Product.objects.create(
            vendor=self.grill, name_ar="تكة", description_ar="قطع لحم مشوية على الفحم", price=8000
        )
        Product.objects.create(vendor=self.burger, name_ar="برغر كلاسيك", name_en="Classic burger", price=7000)
        Product.objects.create(vendor=self.burger, name_ar="كباب قديم", price=1, is_archived=True)
        Vendor.objects.create(
            owner=owner, name="برغر لم يُعتمد", location=Point(44.42, 33.305, srid=4326)
        )  # still waiting for approval
        self.client = APIClient()

    def find(self, q, **params):
        response = self.client.get("/api/vendors/", {"q": q, **KARRADA, **params})
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def test_folding_evens_out_arabic_spellings(self):
        self.assertEqual(fold("  أحمد  إبراهيم آمنة "), fold("احمد ابراهیم امنه"))
        self.assertEqual(fold("كَبَابٌ"), fold("کباب"))
        self.assertEqual(fold("Burger"), "burger")

    def test_finds_stores_by_name_and_dish_with_the_matching_dishes(self):
        by_dish = self.find("كباب")
        self.assertEqual([s["name"] for s in by_dish], ["مطعم دجلة للمشويات"])  # archived dishes don't count
        self.assertEqual([m["name_ar"] for m in by_dish[0]["matches"]], ["كباب عراقي"])
        self.assertEqual([s["name"] for s in self.find("الكراده")], ["برغر الكرادة"])  # ه for ة
        self.assertEqual([s["name"] for s in self.find("kebab")], ["مطعم دجلة للمشويات"])
        self.assertEqual([s["name"] for s in self.find("لحم مشوي")], ["مطعم دجلة للمشويات"])  # descriptions

    def test_a_kind_of_place_finds_every_place_of_that_kind(self):
        self.assertEqual([s["name"] for s in self.find("صيدليه")], ["صيدلية الشفاء"])
        self.assertEqual([s["name"] for s in self.find("pharmacy")], ["صيدلية الشفاء"])
        self.assertEqual([s["name"] for s in self.find("ورد")], ["Karrada Flowers"])
        self.assertEqual({s["name"] for s in self.find("burger")}, {"برغر الكرادة"})

    def test_store_names_come_before_menu_matches(self):
        Product.objects.create(vendor=self.grill, name_ar="برغر لحم", price=8000)
        self.assertEqual([s["name"] for s in self.find("برغر")], ["برغر الكرادة", "مطعم دجلة للمشويات"])

    def test_no_match_and_blank_queries(self):
        self.assertEqual(self.find("سوشي"), [])
        self.assertEqual(len(self.client.get("/api/vendors/", {"q": "  ", **KARRADA}).json()["results"]), 4)

    def test_type_filter_covers_the_new_kinds(self):
        response = self.client.get("/api/vendors/", {"type": "pharmacy", **KARRADA}).json()["results"]
        self.assertEqual([(s["name"], s["type"]) for s in response], [("صيدلية الشفاء", "pharmacy")])


class OfferBadgeTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(phone="+9647800000090", role=User.Role.VENDOR)
        self.deals = store(owner, "Deals Grill")
        self.plain = store(owner, "Plain Grill", lng=44.421)
        now = timezone.now()
        week = {"starts_at": now - timedelta(hours=1), "ends_at": now + timedelta(days=7)}
        Offer.objects.create(vendor=self.deals, title="Free ride", type="free_delivery", **week)
        Offer.objects.create(vendor=self.deals, title="10% off", type="percent", value=10, **week)
        Offer.objects.create(
            vendor=self.plain, title="Last week", type="percent", value=50,
            starts_at=now - timedelta(days=8), ends_at=now - timedelta(days=1),
        )

    def test_cards_show_the_headline_running_offer(self):
        stores = {s["name"]: s for s in APIClient().get("/api/vendors/", KARRADA).json()["results"]}
        self.assertEqual((stores["Deals Grill"]["offer"]["title"], stores["Deals Grill"]["offer"]["value"]), ("10% off", "10"))
        self.assertIsNone(stores["Plain Grill"]["offer"])  # ended offers don't count

    def test_offers_filter_keeps_stores_with_a_running_offer(self):
        stores = APIClient().get("/api/vendors/", {"offers": "1", **KARRADA}).json()["results"]
        self.assertEqual([s["name"] for s in stores], ["Deals Grill"])


class NewTypeOnboardingTests(TestCase):
    def test_only_restaurants_keep_a_cuisine(self):
        owner = User.objects.create_user(phone="+9647800000095")
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/store-applications/",
            {
                "name": "Rose Shop", "type": "flowers", "cuisine": "sweets", "address": "Karrada",
                "latitude": 33.305, "longitude": 44.42, "owner_name": "Sara",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        shop = Vendor.objects.get(name="Rose Shop")
        self.assertEqual((shop.type, shop.cuisine), ("flowers", ""))
