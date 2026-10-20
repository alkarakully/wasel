import io
import os
import shutil
import tempfile
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from orders.models import Order

from .models import Offer, Product, StoreMember, Vendor

MEDIA = tempfile.mkdtemp()


def photo(size=(2400, 1600), fmt="PNG", mode="RGBA"):
    buffer = io.BytesIO()
    Image.new(mode, size, (200, 40, 40, 255) if mode == "RGBA" else (200, 40, 40)).save(buffer, fmt)
    return SimpleUploadedFile(f"dish.{fmt.lower()}", buffer.getvalue(), content_type=f"image/{fmt.lower()}")


@override_settings(MEDIA_ROOT=MEDIA)
class ProductPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = User.objects.create_user(phone="+9647800000060", role=User.Role.VENDOR)
        self.store = Vendor.objects.create(
            status=Vendor.Status.APPROVED, owner=self.owner, name="Photo Grill", location=Point(44.4, 33.34, srid=4326)
        )
        self.product = Product.objects.create(vendor=self.store, name_ar="تكة", price=8000)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def upload(self, file, product=None):
        return self.client.post(f"/api/products/{(product or self.product).pk}/image/", {"image": file}, format="multipart")

    def test_owner_uploads_a_photo_that_is_shrunk_to_jpeg(self):
        response = self.upload(photo())
        self.assertEqual(response.status_code, 200)
        url = response.json()["image"]
        self.assertTrue(url.startswith("/media/products/") and url.endswith(".jpg"))
        self.product.refresh_from_db()
        with Image.open(self.product.image.path) as saved:
            self.assertEqual(saved.format, "JPEG")
            self.assertEqual(max(saved.size), 1200)

    def test_customers_see_the_photo_and_description(self):
        self.client.patch(f"/api/products/{self.product.pk}/", {"description_ar": "لحم مشوي"}, format="json")
        self.upload(photo((300, 300), "JPEG", "RGB"))
        item = APIClient().get(f"/api/vendors/{self.store.pk}/").json()["products"][0]
        self.assertEqual(item["description_ar"], "لحم مشوي")
        self.assertTrue(item["image"].startswith("/media/products/"))

    def test_replacing_or_removing_deletes_the_old_file(self):
        self.upload(photo())
        self.product.refresh_from_db()
        first = self.product.image.path
        self.upload(photo((800, 800)))
        self.product.refresh_from_db()
        self.assertNotEqual(self.product.image.path, first)
        self.assertFalse(os.path.exists(first))
        second = self.product.image.path
        response = self.client.delete(f"/api/products/{self.product.pk}/image/")
        self.assertIsNone(response.json()["image"])
        self.assertFalse(os.path.exists(second))

    def test_a_file_that_isnt_a_photo_is_refused(self):
        bad = SimpleUploadedFile("menu.pdf", b"%PDF-1.4 not a picture", content_type="application/pdf")
        response = self.upload(bad)
        self.assertEqual((response.status_code, response.json()["error"]), (400, "invalid_image"))
        self.assertEqual(self.client.post(f"/api/products/{self.product.pk}/image/", {}, format="multipart").json()["error"], "image_required")

    def test_cashiers_and_other_stores_cannot_change_photos(self):
        cashier = User.objects.create_user(phone="+9647800000061")
        StoreMember.objects.create(vendor=self.store, user=cashier, role=StoreMember.Role.CASHIER)
        stranger = User.objects.create_user(phone="+9647800000062", role=User.Role.VENDOR)
        for user in (cashier, stranger):
            self.client.force_authenticate(user)
            self.assertEqual(self.upload(photo((100, 100))).status_code, 403)


class StoreOfferTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="+9647800000070", role=User.Role.VENDOR)
        self.store = Vendor.objects.create(
            status=Vendor.Status.APPROVED, owner=self.owner, name="Offer Grill", location=Point(44.4, 33.34, srid=4326)
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        now = timezone.now()
        self.week = {"starts_at": (now - timedelta(minutes=1)).isoformat(), "ends_at": (now + timedelta(days=7)).isoformat()}
        self.url = f"/api/vendors/{self.store.pk}/offers/"

    def test_owner_creates_an_offer_customers_see_on_the_store(self):
        response = self.client.post(self.url, {"title": "خصم 10%", "type": "percent", "value": "10", "min_order": "15000", **self.week}, format="json")
        self.assertEqual(response.status_code, 201)
        row = response.json()
        self.assertEqual((row["value"], row["min_order"], row["currency"], row["state"]), ("10", "15000", "IQD", "running"))
        offers = APIClient().get(f"/api/vendors/{self.store.pk}/").json()["offers"]
        self.assertEqual([o["title"] for o in offers], ["خصم 10%"])
        self.assertFalse(Offer.objects.get().is_banner)

    def test_free_delivery_needs_no_value(self):
        response = self.client.post(self.url, {"title": "توصيل مجاني", "type": "free_delivery", **self.week}, format="json")
        self.assertEqual((response.status_code, response.json()["value"]), (201, "0"))

    def test_rules_are_checked(self):
        cases = [
            ({"type": "percent", "value": "150"}, "value"),
            ({"type": "fixed", "value": "0"}, "value"),
            ({"type": "fixed", "value": "1000.5"}, "value"),  # dinars have no decimals
            ({"type": "bundle", "value": "1"}, "type"),
            ({"type": "bogo"}, "product"),
            ({"type": "percent", "value": "10", "ends_at": self.week["starts_at"]}, "ends_at"),
        ]
        for extra, field in cases:
            response = self.client.post(self.url, {"title": "x", **self.week, **extra}, format="json")
            self.assertEqual(response.status_code, 400, extra)
            self.assertIn(field, response.json(), extra)

    def test_edit_list_and_end(self):
        offer = self.client.post(self.url, {"title": "A", "type": "fixed", "value": "2000", **self.week}, format="json").json()
        edited = self.client.patch(f"{self.url}{offer['id']}/", {"value": "3000"}, format="json").json()
        self.assertEqual(edited["value"], "3000")
        self.assertEqual([o["id"] for o in self.client.get(self.url).json()], [offer["id"]])
        # Used offers end instead of disappearing, so old orders keep them.
        customer = User.objects.create_user(phone="+9647800000073")
        Order.objects.create(customer=customer, vendor=self.store, offer_id=offer["id"], subtotal=20000, delivery_address="x", delivery_location=Point(44.4, 33.34, srid=4326))
        self.assertEqual(self.client.delete(f"{self.url}{offer['id']}/").status_code, 204)
        self.assertEqual(self.client.get(self.url).json()[0]["state"], "ended")

    def test_buy_one_get_one_free_is_on_one_of_the_stores_items(self):
        burger = Product.objects.create(vendor=self.store, name_ar="برغر", name_en="Burger", price=7000)
        dates = Product.objects.create(vendor=self.store, name_ar="تمر", price=5000, unit_type=Product.UnitType.KG)
        other_store = Vendor.objects.create(
            status=Vendor.Status.APPROVED, owner=User.objects.create_user(phone="+9647800000074"),
            name="Other", location=Point(44.4, 33.34, srid=4326),
        )
        theirs = Product.objects.create(vendor=other_store, name_ar="x", price=1000)
        for product, field in [(None, "product"), (dates.pk, "product"), (theirs.pk, "product")]:
            response = self.client.post(self.url, {"title": "1+1", "type": "bogo", "product": product, **self.week}, format="json")
            self.assertEqual(response.status_code, 400, product)
            self.assertIn(field, response.json())
        response = self.client.post(self.url, {"title": "1+1", "type": "bogo", "product": burger.pk, **self.week}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["product"], response.json()["value"]), (burger.pk, "0"))
        offer = APIClient().get(f"/api/vendors/{self.store.pk}/").json()["offers"][0]
        self.assertEqual((offer["type"], offer["product"]["name_en"]), ("bogo", "Burger"))
        # One deal per item at a time.
        again = self.client.post(self.url, {"title": "Again", "type": "bogo", "product": burger.pk, **self.week}, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertIn("product", again.json())

    def test_unused_offer_is_deleted(self):
        offer = self.client.post(self.url, {"title": "A", "type": "percent", "value": "5", **self.week}, format="json").json()
        self.client.delete(f"{self.url}{offer['id']}/")
        self.assertFalse(Offer.objects.exists())

    def test_cashiers_and_other_stores_cannot_run_offers(self):
        mine = Offer.objects.create(vendor=self.store, title="A", type="percent", value=5, **self.week)
        cashier = User.objects.create_user(phone="+9647800000071")
        StoreMember.objects.create(vendor=self.store, user=cashier, role=StoreMember.Role.CASHIER)
        stranger = User.objects.create_user(phone="+9647800000072", role=User.Role.VENDOR)
        for user in (cashier, stranger):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, {"title": "x", "type": "percent", "value": "5", **self.week}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(f"{self.url}{mine.pk}/").status_code, 403)
        self.assertTrue(Offer.objects.filter(pk=mine.pk).exists())
