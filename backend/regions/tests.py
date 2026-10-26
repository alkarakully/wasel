"""Wasel outside Iraq: phones from anywhere, and a Kuwaiti store in dinars with three decimals."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, WalletTransaction
from accounts.tests import TEST_OTP, RecordingSender
from billing.weeks import close_week, week_start
from console.access import VERIFIED
from console.models import StaffProfile
from console.staff import create_staff
from orders.models import Order
from vendors.models import Product, Vendor

from .regions import as_api, quantize, where

KUWAIT_CITY = (29.3759, 47.9774)
NEAR_KUWAIT = (29.3800, 47.9774)  # about 450 m north


class RegistryTests(TestCase):
    def test_countries_list_puts_iraq_and_the_gulf_first(self):
        data = APIClient().get("/api/countries/").json()
        codes = [c["code"] for c in data["countries"]]
        self.assertEqual(codes[:7], ["IQ", "SA", "AE", "KW", "QA", "BH", "OM"])
        self.assertEqual(data["short_list"], codes[:7])
        self.assertIn("GB", codes)
        self.assertEqual(codes[7:], sorted(codes[7:], key=lambda c: next(x["name_en"] for x in data["countries"] if x["code"] == c)))
        kw = next(r for r in data["regions"] if r["country"] == "KW")
        self.assertEqual((kw["currency"], kw["decimals"], kw["time_zone"]), ("KWD", 3, "Asia/Kuwait"))
        self.assertEqual(kw["tips"], ["0.250", "0.500", "1.000"])

    def test_money_keeps_each_currencys_decimals(self):
        self.assertEqual(as_api(Decimal("18000"), "IQD"), "18000")
        self.assertEqual(as_api(Decimal("12.5"), "SAR"), "12.50")
        self.assertEqual(as_api(Decimal("0.75"), "KWD"), "0.750")
        self.assertEqual(quantize(Decimal("1499.5"), "IQD"), Decimal("1500"))
        self.assertEqual(quantize(Decimal("1.2345"), "KWD"), Decimal("1.235"))

    def test_where_a_map_spot_is(self):
        self.assertEqual(where(33.31, 44.36), "IQ")  # Baghdad
        self.assertEqual(where(*KUWAIT_CITY), "KW")  # inside Iraq's rough box too
        self.assertEqual(where(25.2, 55.27), "AE")  # Dubai
        self.assertEqual(where(24.71, 46.67), "SA")  # Riyadh
        self.assertIsNone(where(51.5, -0.12))  # London

    def test_each_country_starts_its_week_on_its_own_day(self):
        wednesday = date(2026, 10, 21)
        self.assertEqual(week_start(wednesday, "IQ"), date(2026, 10, 17))  # Saturday
        self.assertEqual(week_start(wednesday, "SA"), date(2026, 10, 18))  # Sunday
        self.assertEqual(week_start(wednesday, "AE"), date(2026, 10, 19))  # Monday


@override_settings(OTP=TEST_OTP)
class ForeignPhoneSignInTests(TestCase):
    def setUp(self):
        cache.clear()
        RecordingSender.sent = []
        RecordingSender.failing = set()
        self.client = APIClient()

    def sign_in(self, phone, country):
        sent = self.client.post("/api/auth/otp/request/", {"phone": phone, "country": country}, format="json")
        self.assertEqual(sent.status_code, 200, sent.content)
        code = RecordingSender.sent[-1][2]
        return sent.json()["phone"], self.client.post(
            "/api/auth/otp/verify/", {"phone": phone, "country": country, "code": code}, format="json"
        )

    def test_saudi_emirati_and_british_numbers_sign_in(self):
        for raw, country, e164, home in [
            ("050 123 4567", "SA", "+966501234567", "SA"),
            ("0501234567", "AE", "+971501234567", "AE"),
            ("07700 900123", "GB", "+447700900123", "GB"),
        ]:
            with self.subTest(country=country):
                phone, verified = self.sign_in(raw, country)
                self.assertEqual(phone, e164)
                self.assertEqual(verified.status_code, 201, verified.content)  # a new account
                self.assertEqual(verified.json()["user"]["country"], home)
                self.assertEqual(User.objects.get(phone=e164).country, home)

    def test_old_apps_without_a_country_are_read_as_iraq(self):
        response = self.client.post("/api/auth/otp/request/", {"phone": "0770 123 4567"}, format="json")
        self.assertEqual(response.json()["phone"], "+9647701234567")

    def test_a_number_that_doesnt_fit_the_country_is_explained(self):
        response = self.client.post("/api/auth/otp/request/", {"phone": "0770123456", "country": "SA"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Saudi Arabia", str(response.json()))


class KuwaitStoreTests(TestCase):
    """A store in Kuwait prices, charges, refunds and bills in KWD with three decimals, on Kuwait's calendar."""

    def setUp(self):
        self.customer = User.objects.create_user("+96555123456", wallet_balance=Decimal("10"))
        self.owner = User.objects.create_user("+96566123456", role=User.Role.VENDOR)
        self.store = Vendor.objects.create(
            owner=self.owner,
            name="Gulf Grill",
            location=Point(KUWAIT_CITY[1], KUWAIT_CITY[0], srid=4326),
            country="KW",
            status=Vendor.Status.APPROVED,
            is_open=True,
            commission_rate=Decimal("15"),
        )
        self.shawarma = Product.objects.create(vendor=self.store, name_ar="شاورما", price=Decimal("1.250"))
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def cart(self, **extra):
        return {
            "vendor": self.store.pk,
            "items": [{"product": self.shawarma.pk, "quantity": 2}],
            "delivery_latitude": NEAR_KUWAIT[0],
            "delivery_longitude": NEAR_KUWAIT[1],
            **extra,
        }

    @override_settings(PAYMENT_METHODS=["cod", "wallet"])  # the wallet is off by default
    def test_quote_order_refund_and_statement(self):
        self.assertEqual(self.customer.country, "KW")
        quote = self.client.post("/api/orders/quote/", self.cart(), format="json").json()
        self.assertEqual(quote["currency"], "KWD")
        self.assertEqual(
            [quote[k] for k in ("subtotal", "delivery_fee", "service_fee", "total_amount")],
            ["2.500", "0.500", "0.150", "3.150"],
        )

        placed = self.client.post(
            "/api/orders/", {**self.cart(), "delivery_address": "Salmiya", "payment_type": "wallet"}, format="json"
        )
        self.assertEqual(placed.status_code, 201, placed.content)
        order = Order.objects.get(pk=placed.json()["id"])
        self.assertEqual((order.currency, order.commission_amount), ("KWD", Decimal("0.375")))
        self.assertEqual(placed.json()["total_amount"], "3.150")
        self.assertEqual(placed.json()["items"][0]["unit_price"], "1.250")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.wallet_balance, Decimal("6.850"))

        self.client.post(f"/api/orders/{order.pk}/cancel/", {}, format="json")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.wallet_balance, Decimal("10"))
        self.assertEqual(
            list(WalletTransaction.objects.values_list("type", "currency", "amount").order_by("id")),
            [("payment", "KWD", Decimal("-3.150")), ("refund", "KWD", Decimal("3.150"))],
        )

    def test_weekly_statement_in_kwd(self):
        sunday = date(2026, 10, 11)
        Order.objects.create(
            customer=self.customer,
            vendor=self.store,
            currency="KWD",
            status=Order.Status.DELIVERED,
            delivery_address="Salmiya",
            delivery_location=self.store.location,
            subtotal=Decimal("2.500"),
            commission_amount=Decimal("0.375"),
            total_amount=Decimal("3.150"),
            delivered_at=datetime(2026, 10, 13, 12, tzinfo=ZoneInfo("Asia/Kuwait")),
        )
        self.assertEqual(close_week(sunday, "IQ"), [])  # Iraq's stores only
        [statement] = close_week(sunday, "KW")
        self.assertEqual((statement.currency, statement.period_end), ("KWD", date(2026, 10, 17)))
        self.assertEqual(statement.payout, Decimal("2.125"))

    @override_settings(PAYMENT_METHODS=["cod", "wallet"])  # the wallet is off by default
    def test_iraqi_wallet_cant_pay_a_kuwaiti_store(self):
        iraqi = User.objects.create_user("+9647700000999", wallet_balance=Decimal("100000"))
        self.client.force_authenticate(iraqi)
        response = self.client.post(
            "/api/orders/", {**self.cart(), "delivery_address": "Salmiya", "payment_type": "wallet"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "wallet_currency_mismatch")

    def test_prices_follow_the_currencys_decimals(self):
        self.client.force_authenticate(self.owner)
        url = f"/api/vendors/{self.store.pk}/products/"
        self.assertEqual(self.client.post(url, {"name_ar": "x", "price": "1.2505"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"name_ar": "x", "price": "1.250"}, format="json").status_code, 201)

        iraqi_owner = User.objects.create_user("+9647800000777", role=User.Role.VENDOR)
        iraqi = Vendor.objects.create(
            owner=iraqi_owner, name="Tigris", location=Point(44.36, 33.31, srid=4326), status=Vendor.Status.APPROVED
        )
        self.client.force_authenticate(iraqi_owner)
        response = self.client.post(f"/api/vendors/{iraqi.pk}/products/", {"name_ar": "x", "price": "1500.5"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("whole", str(response.json()))

    def test_platform_offers_only_apply_in_their_country(self):
        from vendors.models import Offer

        now = timezone.now()
        Offer.objects.create(
            title="Iraq 50%", type=Offer.Type.PERCENT, value=50, starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(days=1), country="IQ",
        )
        quote = self.client.post("/api/orders/quote/", self.cart(), format="json").json()
        self.assertEqual(quote["discount"], "0.000")
        Offer.objects.create(
            title="Kuwait 1 KD off", type=Offer.Type.FIXED, value=Decimal("1"), starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(days=1), country="KW",
        )
        quote = self.client.post("/api/orders/quote/", self.cart(), format="json").json()
        self.assertEqual(quote["discount"], "1.000")


class ConsoleCountryTests(TestCase):
    def setUp(self):
        self.admin = create_staff("admin@wasel.iq", "Admin", StaffProfile.Role.ADMIN, "lapis-and-gold-2026")
        self.client.force_login(self.admin.user)
        session = self.client.session
        session[VERIFIED] = self.admin.user_id
        session.save()
        customer = User.objects.create_user("+96555123456")
        for country, lat, lng, total in [("KW", *KUWAIT_CITY, Decimal("3.150")), ("IQ", 33.31, 44.36, Decimal("10000"))]:
            owner = User.objects.create_user(f"+9647800000{len(country) * 100 + int(total) % 97:03d}", role=User.Role.VENDOR)
            store = Vendor.objects.create(
                owner=owner, name=f"Store {country}", location=Point(lng, lat, srid=4326), country=country,
                status=Vendor.Status.APPROVED,
            )
            Order.objects.create(
                customer=customer, vendor=store, currency=store.currency, status=Order.Status.DELIVERED,
                delivery_address="x", delivery_location=store.location, total_amount=total, subtotal=total,
                delivered_at=timezone.now(),
            )

    def test_overview_is_for_one_country_at_a_time(self):
        iraq = self.client.get("/api/console/overview/").json()
        self.assertEqual((iraq["currency"], iraq["today"]["sales"]), ("IQD", "10000"))
        kuwait = self.client.get("/api/console/overview/?country=KW").json()
        self.assertEqual((kuwait["currency"], kuwait["today"]["sales"], kuwait["live"]["stores"]), ("KWD", "3.150", 1))

    def test_create_a_store_in_the_emirates(self):
        response = self.client.post(
            "/api/console/stores/",
            {"name": "Dubai Diner", "latitude": 25.2, "longitude": 55.27, "owner_phone": "050 111 2233", "owner_country": "AE"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["country"], response.json()["currency"]), ("AE", "AED"))
        self.assertEqual(response.json()["time_zone"], "Asia/Dubai")
        self.assertEqual(Vendor.objects.get(name="Dubai Diner").owner.phone, "+971501112233")

    def test_store_outside_its_country_is_refused(self):
        response = self.client.post(
            "/api/console/stores/",
            {"name": "X", "latitude": 51.5, "longitude": -0.12, "owner_phone": "07801112233"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("country", response.json())
