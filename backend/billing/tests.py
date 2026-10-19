from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from orders.models import Order, OrderItem
from vendors.models import Offer, Product, StoreMember, Vendor

from .models import Statement
from .weeks import close_week, week_start

BAGHDAD = Point(44.4214, 33.3045, srid=4326)


def at(day, hour=13):
    return timezone.make_aware(datetime.combine(day, time(hour)))


class StoreTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("+9647800000700", role=User.Role.VENDOR, name="Owner")
        self.store = Vendor.objects.create(
            status=Vendor.Status.APPROVED,
            owner=self.owner, name="Tigris Grill", location=BAGHDAD, is_open=True, commission_rate=Decimal("15")
        )
        self.kebab = Product.objects.create(vendor=self.store, name_ar="كباب", name_en="Kebab", price=9000)
        self.customer = User.objects.create_user("+9647700000701")
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def member(self, role, phone="+9647800000702"):
        user = User.objects.create_user(phone, role=User.Role.VENDOR)
        StoreMember.objects.create(vendor=self.store, user=user, role=role)
        return user

    def order(self, when, status=Order.Status.DELIVERED, subtotal=10000, commission=1500, discount=0, offer=None):
        o = Order.objects.create(
            customer=self.customer,
            vendor=self.store,
            status=status,
            delivery_address="Karrada",
            delivery_location=BAGHDAD,
            subtotal=subtotal,
            discount=discount,
            offer=offer,
            commission_amount=commission,
            total_amount=subtotal - discount + 2000,
            delivered_at=when if status == Order.Status.DELIVERED else None,
        )
        Order.objects.filter(pk=o.pk).update(created_at=when)
        OrderItem.objects.create(order=o, product=self.kebab, quantity=1, unit_price=subtotal, line_total=subtotal)
        return o


class TeamTests(StoreTestCase):
    def test_owner_invites_a_cashier_who_joins_on_accepting(self):
        response = self.client.post(
            f"/api/vendors/{self.store.pk}/team/", {"phone": "0780 111 2233", "name": "Sara", "role": "cashier"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        # Nothing is created for the number until its owner says yes.
        self.assertFalse(User.objects.filter(phone="+9647801112233").exists())
        team = self.client.get(f"/api/vendors/{self.store.pk}/team/").data
        self.assertEqual(team["owner"]["role"], "owner")
        self.assertEqual(team["members"], [])
        self.assertEqual([(i["name"], i["role"]) for i in team["invites"]], [("Sara", "cashier")])

        sara = User.objects.create_user("+9647801112233")  # signs in for the first time
        self.client.force_authenticate(sara)
        invite = self.client.get("/api/store-invites/").data[0]
        self.assertEqual(invite["store"]["name"], "Tigris Grill")
        self.assertEqual(self.client.post(f"/api/store-invites/{invite['id']}/accept/").status_code, 200)
        sara.refresh_from_db()
        self.assertEqual((sara.role, sara.name), (User.Role.VENDOR, "Sara"))
        self.assertEqual(self.client.get("/api/vendors/mine/").data[0]["my_role"], "cashier")

    def test_customers_with_orders_cant_be_invited_and_nobody_twice(self):
        self.order(timezone.now())  # 07700000701 is a real customer
        response = self.client.post(f"/api/vendors/{self.store.pk}/team/", {"phone": "07700000701"}, format="json")
        self.assertEqual(response.data["error"], "phone_in_use")
        self.member("cashier")
        response = self.client.post(f"/api/vendors/{self.store.pk}/team/", {"phone": "07800000702"}, format="json")
        self.assertEqual(response.data["error"], "already_member")
        self.client.post(f"/api/vendors/{self.store.pk}/team/", {"phone": "07800000799"}, format="json")
        response = self.client.post(f"/api/vendors/{self.store.pk}/team/", {"phone": "07800000799"}, format="json")
        self.assertEqual(response.data["error"], "already_invited")

    def test_cashiers_run_orders_but_not_menu_reports_billing_or_team(self):
        cashier = self.member("cashier")
        self.client.force_authenticate(cashier)
        new = self.order(timezone.now(), status=Order.Status.RECEIVED)

        mine = self.client.get("/api/vendors/mine/").data
        self.assertEqual(mine[0]["my_role"], "cashier")
        self.assertEqual(self.client.get("/api/orders/?status=received").data["results"][0]["id"], new.pk)
        accepted = self.client.post(f"/api/orders/{new.pk}/accept/", {"prep_minutes": 15}, format="json")
        self.assertEqual(accepted.status_code, 200)

        self.assertEqual(self.client.post(f"/api/vendors/{self.store.pk}/products/", {"name_ar": "x", "price": 1}).status_code, 403)
        self.assertEqual(self.client.get(f"/api/vendors/{self.store.pk}/report/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/vendors/{self.store.pk}/billing/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/vendors/{self.store.pk}/team/").status_code, 403)

    def test_managers_edit_the_menu_and_see_reports_but_not_billing(self):
        self.client.force_authenticate(self.member("manager"))
        self.assertEqual(self.client.get(f"/api/vendors/{self.store.pk}/report/").status_code, 200)
        self.assertEqual(
            self.client.patch(f"/api/products/{self.kebab.pk}/", {"price": "9500"}, format="json").status_code, 200
        )
        self.assertEqual(self.client.get(f"/api/vendors/{self.store.pk}/billing/").status_code, 403)

    def test_removed_members_lose_access(self):
        user = self.member("cashier")
        member = StoreMember.objects.get(user=user)
        self.client.delete(f"/api/vendors/{self.store.pk}/team/{member.pk}/")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/vendors/mine/").data, [])

    @mock.patch("orders.services.notify")
    def test_the_whole_team_hears_new_orders(self, notify):
        cashier = self.member("cashier")
        customer = APIClient()
        customer.force_authenticate(self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            customer.post(
                "/api/orders/",
                {"vendor": self.store.pk, "items": [{"product": self.kebab.pk, "quantity": "1"}],
                 "delivery_latitude": 33.3045, "delivery_longitude": 44.4214,
                 "delivery_address": "Karrada", "payment_type": "cod"},
                format="json",
            )
        told = {c.args[0] for c in notify.call_args_list if c.args[2] == "store_new_order"}
        self.assertEqual(told, {self.owner.pk, cashier.pk})


class MenuAndHoursTests(StoreTestCase):
    def test_add_edit_and_remove_items(self):
        response = self.client.post(
            f"/api/vendors/{self.store.pk}/products/",
            {"name_ar": "تكة", "name_en": "Tikka", "menu_section": "Grill", "price": "8000", "unit_type": "item"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        tikka = Product.objects.get(name_en="Tikka")

        self.client.patch(f"/api/products/{tikka.pk}/", {"price": "8500", "menu_section": "Mains"}, format="json")
        tikka.refresh_from_db()
        self.assertEqual((tikka.price, tikka.menu_section), (Decimal("8500"), "Mains"))

        self.client.delete(f"/api/products/{tikka.pk}/")
        self.assertFalse(Product.objects.filter(pk=tikka.pk).exists())

    def test_ordered_items_are_archived_not_deleted(self):
        self.order(timezone.now())
        self.client.delete(f"/api/products/{self.kebab.pk}/")
        self.kebab.refresh_from_db()
        self.assertTrue(self.kebab.is_archived)
        menu = self.client.get(f"/api/vendors/{self.store.pk}/").data["products"]
        self.assertEqual(menu, [])

    def test_prices_must_be_positive_and_names_present(self):
        response = self.client.post(f"/api/vendors/{self.store.pk}/products/", {"name_ar": " ", "price": "0"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.data)
        self.assertIn("name_ar", response.data)

    def test_opening_hours(self):
        hours = {"sat": ["10:00", "23:30"], "sun": ["18:00", "02:00"], "fri": None}
        response = self.client.put(f"/api/vendors/{self.store.pk}/hours/", hours, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.store.refresh_from_db()
        self.assertEqual(self.store.opening_hours["sun"], ["18:00", "02:00"])
        self.assertIsNone(self.store.opening_hours["mon"])

        bad = self.client.put(f"/api/vendors/{self.store.pk}/hours/", {"sat": ["25:00", "10:00"]}, format="json")
        self.assertEqual(bad.data["error"], "invalid_hours")


class ReportTests(StoreTestCase):
    def test_numbers_for_a_range(self):
        today = timezone.localdate()
        self.order(at(today), subtotal=10000, commission=1500)
        self.order(at(today - timedelta(days=1)), subtotal=20000, commission=3000)
        self.order(at(today), status=Order.Status.CANCELLED)
        self.order(at(today - timedelta(days=30)))  # outside the range

        report = self.client.get(f"/api/vendors/{self.store.pk}/report/").data
        self.assertEqual(report["orders"], 3)
        self.assertEqual(report["delivered"], 2)
        self.assertEqual(report["cancelled"], 1)
        self.assertEqual(report["food_sales"], "30000")
        self.assertEqual(report["commission"], "4500")
        self.assertEqual(report["payout"], "25500")
        self.assertEqual(report["average_order"], "15000")
        self.assertEqual(len(report["days"]), 7)
        self.assertEqual(report["days"][-1], {"date": today.isoformat(), "orders": 1, "sales": "10000"})
        self.assertEqual(report["top_items"][0]["name"]["en"], "Kebab")
        self.assertEqual(report["top_items"][0]["sales"], "30000")

    def test_bad_ranges(self):
        response = self.client.get(f"/api/vendors/{self.store.pk}/report/?from=2026-05-02&to=2026-05-01")
        self.assertEqual(response.data["error"], "invalid_range")


class StatementTests(StoreTestCase):
    def test_weeks_run_saturday_to_friday(self):
        self.assertEqual(week_start(date(2026, 10, 17)), date(2026, 10, 17))  # Saturday
        self.assertEqual(week_start(date(2026, 10, 23)), date(2026, 10, 17))  # Friday
        self.assertEqual(week_start(date(2026, 10, 24)), date(2026, 10, 24))

    def test_closing_a_week_and_paying_it(self):
        start = date(2026, 10, 10)
        own_offer = Offer.objects.create(
            vendor=self.store, title="10% off", type=Offer.Type.PERCENT, value=10,
            starts_at=at(start), ends_at=at(start + timedelta(days=30)),
        )
        wasel_offer = Offer.objects.create(
            title="Wasel pays", type=Offer.Type.FIXED, value=1000,
            starts_at=at(start), ends_at=at(start + timedelta(days=30)),
        )
        self.order(at(start), subtotal=10000, commission=1350, discount=1000, offer=own_offer)
        self.order(at(start + timedelta(days=6), 23), subtotal=20000, commission=3000, discount=1000, offer=wasel_offer)
        self.order(at(start + timedelta(days=7)))  # next week
        self.order(at(start + timedelta(days=2)), status=Order.Status.CANCELLED)

        made = close_week(start)
        self.assertEqual(len(made), 1)
        statement = made[0]
        self.assertEqual(statement.orders_count, 2)
        self.assertEqual(statement.food_sales, 30000)
        self.assertEqual(statement.store_discounts, 1000)  # only the store's own offer
        self.assertEqual(statement.commission, 4350)
        self.assertEqual(statement.payout, 24650)
        self.assertEqual(close_week(start), [])  # safe to run again

        billing = self.client.get(f"/api/vendors/{self.store.pk}/billing/").data
        self.assertEqual(billing["due_total"], "24650")
        self.assertEqual(billing["statements"][0]["status"], "due")

        detail = self.client.get(f"/api/vendors/{self.store.pk}/statements/{statement.pk}/").data
        self.assertEqual([line["payout"] for line in detail["orders"]], ["7650", "17000"])
        csv = self.client.get(f"/api/vendors/{self.store.pk}/statements/{statement.pk}/?download=csv")
        self.assertIn("Tigris Grill", csv.content.decode("utf-8-sig"))

        staff = User.objects.create_superuser("+9647700000799", "a-strong-admin-pass")
        self.client.force_authenticate(None)
        web = self.client
        web.force_login(staff)
        due = web.get("/api/ops/payouts/?status=due").json()
        self.assertEqual(due["due_total"], "24650")
        web.post(f"/api/ops/payouts/{statement.pk}/paid/", {"reference": "TRF-1001"}, content_type="application/json")
        statement.refresh_from_db()
        self.assertEqual((statement.status, statement.paid_reference), ("paid", "TRF-1001"))

    def test_this_week_is_live(self):
        self.order(timezone.now(), subtotal=12000, commission=1800)
        current = self.client.get(f"/api/vendors/{self.store.pk}/billing/").data["current_week"]
        self.assertEqual(current["orders_count"], 1)
        self.assertEqual(current["payout"], "10200")
