from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from accounts.models import User, WalletTransaction
from billing.models import Statement
from orders.models import CaptainLocation, DispatchOffer, Order, StuckOrderAlert
from vendors.models import Offer, Product, StoreMember, Vendor

from . import totp
from .access import VERIFIED
from .models import AuditEntry, StaffProfile
from .staff import create_staff

BAGHDAD = Point(44.4214, 33.3045, srid=4326)
PASSWORD = "lapis-and-gold-2026"


class TotpTests(TestCase):
    """RFC 6238 test vectors (SHA-1, 8 digits there; we check the last 6)."""

    SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32 of "12345678901234567890"

    def test_rfc_vectors(self):
        self.assertEqual(totp.code_at(self.SECRET, 59), "287082")
        self.assertEqual(totp.code_at(self.SECRET, 1111111109), "081804")

    def test_a_code_works_once_and_only_near_its_time(self):
        now = 1_800_000_000
        code = totp.code_at(self.SECRET, now)
        step = totp.verify(self.SECRET, code, now=now)
        self.assertIsNotNone(step)
        self.assertIsNone(totp.verify(self.SECRET, code, last_step=step, now=now))
        self.assertIsNotNone(totp.verify(self.SECRET, code, now=now + 30))
        self.assertIsNone(totp.verify(self.SECRET, code, now=now + 120))
        self.assertIsNone(totp.verify(self.SECRET, "12345", now=now))
        arabic = code.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
        self.assertEqual(totp.verify(self.SECRET, arabic[:3] + " " + arabic[3:], now=now), step)


class ConsoleCase(TestCase):
    def setUp(self):
        cache.clear()  # throttles
        self.admin = create_staff("admin@wasel.iq", "Admin", StaffProfile.Role.ADMIN, PASSWORD)
        self.customer = User.objects.create_user("+9647700000991", name="Zainab")
        self.captain = User.objects.create_user("+9647500000992", role=User.Role.CAPTAIN, name="Ali")
        self.owner = User.objects.create_user("+9647800000993", role=User.Role.VENDOR, name="Owner")
        self.store = Vendor.objects.create(
            owner=self.owner,
            name="Tigris Grill",
            location=BAGHDAD,
            is_open=True,
            status=Vendor.Status.APPROVED,
            commission_rate=Decimal("15"),
        )

    def sign_in(self, profile, client=None):
        client = client or self.client
        client.force_login(profile.user)
        session = client.session
        session[VERIFIED] = profile.user.pk
        session.save()
        return client

    def staff(self, role, email=None):
        return create_staff(email or f"{role}@wasel.iq", role.title(), role, PASSWORD)

    def post(self, url, data=None):
        return self.client.post(url, data or {}, content_type="application/json")

    def patch(self, url, data):
        return self.client.patch(url, data, content_type="application/json")

    def order(self, status=Order.Status.RECEIVED, **extra):
        return Order.objects.create(
            customer=self.customer,
            vendor=self.store,
            status=status,
            delivery_address="Karrada",
            delivery_location=BAGHDAD,
            subtotal=8000,
            total_amount=10000,
            commission_amount=1200,
            service_fee=500,
            delivery_fee=1500,
            **extra,
        )


class SignInTests(ConsoleCase):
    def login(self, email="admin@wasel.iq", password=PASSWORD):
        return self.post("/api/console/auth/login/", {"email": email, "password": password})

    def verify(self, code):
        return self.post("/api/console/auth/verify/", {"code": code})

    def test_first_sign_in_sets_up_the_authenticator(self):
        response = self.login()
        self.assertEqual(response.json()["next"], "setup")
        secret = response.json()["secret"]
        self.assertIn("otpauth://totp/Wasel:admin%40wasel.iq", response.json()["uri"])
        # Password alone doesn't open anything.
        self.assertEqual(self.client.get("/api/console/overview/").status_code, 403)

        response = self.verify(totp.code_at(secret, timezone.now().timestamp()))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["role"], "admin")
        self.assertEqual(self.client.get("/api/console/overview/").status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.totp_enabled)
        self.assertTrue(AuditEntry.objects.filter(action="auth.login", actor_email="admin@wasel.iq").exists())

    def test_later_sign_ins_ask_for_a_code_and_codes_work_once(self):
        self.admin.totp_secret = totp.new_secret()
        self.admin.totp_enabled = True
        self.admin.save()
        self.assertEqual(self.login().json(), {"next": "code"})
        code = totp.code_at(self.admin.totp_secret, timezone.now().timestamp())
        self.assertEqual(self.verify(code).status_code, 200)

        self.post("/api/console/auth/logout/")
        self.login()
        self.assertEqual(self.verify(code).json()["error"], "invalid_code")

    def test_wrong_password_and_unknown_email_look_the_same(self):
        self.assertEqual(self.login(password="nope").json()["error"], "invalid_login")
        self.assertEqual(self.login(email="who@wasel.iq").json()["error"], "invalid_login")

    def test_five_wrong_passwords_lock_the_account(self):
        for _ in range(5):
            self.login(password="nope")
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"], "locked")

    def test_the_code_step_expires(self):
        response = self.login()
        session = self.client.session
        session["console_pending_at"] = (timezone.now() - timedelta(minutes=6)).isoformat()
        session.save()
        code = totp.code_at(response.json()["secret"], timezone.now().timestamp())
        self.assertEqual(self.verify(code).json()["error"], "start_again")

    def test_a_disabled_account_cant_sign_in(self):
        User.objects.filter(pk=self.admin.user_id).update(is_active=False)
        self.assertEqual(self.login().json()["error"], "invalid_login")


class AccessTests(ConsoleCase):
    def test_a_django_admin_session_is_not_enough(self):
        """Signed in with a password only (e.g. the Django admin): no authenticator code, no console."""
        self.client.force_login(self.admin.user)
        self.assertEqual(self.client.get("/api/console/overview/").status_code, 403)

    def test_app_tokens_dont_open_the_console(self):
        from accounts.models import AuthToken as Token

        token = Token.objects.create(user=self.admin.user)
        response = self.client.get("/api/console/overview/", HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(response.status_code, 403)

    def test_changes_need_the_csrf_token(self):
        client = self.sign_in(self.admin, Client(enforce_csrf_checks=True))
        response = client.post(f"/api/console/stores/{self.store.pk}/review/", {"decision": "approve"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])

    def test_roles_see_and_change_only_their_areas(self):
        cases = [
            # role, method, url, allowed
            ("support", "get", "/api/console/orders/", True),
            ("support", "get", "/api/console/payouts/", False),
            ("support", "patch", f"/api/console/stores/{self.store.pk}/", False),
            ("finance", "get", "/api/console/payouts/", True),
            ("finance", "patch", f"/api/console/stores/{self.store.pk}/", False),
            ("marketing", "get", "/api/console/orders/", False),
            ("marketing", "get", "/api/console/offers/", True),
            ("operations", "get", "/api/console/staff/", False),
            ("operations", "get", "/api/console/audit/", False),
        ]
        for role, method, url, allowed in cases:
            with self.subTest(role=role, url=url, method=method):
                self.client.logout()
                self.sign_in(self.staff(role, f"{role}-{method}-{abs(hash(url))}@wasel.iq"))
                response = getattr(self.client, method)(url, {"name": "x"}, content_type="application/json") if method != "get" else self.client.get(url)
                if allowed:
                    self.assertEqual(response.status_code, 200, response.content[:300])
                else:
                    self.assertEqual(response.status_code, 403)

    def test_session_lists_the_areas(self):
        self.sign_in(self.staff("finance"))
        areas = self.client.get("/api/console/auth/session/").json()["user"]["areas"]
        self.assertEqual(areas["money"], "write")
        self.assertEqual(areas["orders"], "read")
        self.assertNotIn("staff", areas)

    def test_django_admin_is_for_superusers_only(self):
        self.client.force_login(self.admin.user)  # staff, not superuser
        response = self.client.get(f"/{settings.DJANGO_ADMIN_PATH}")
        self.assertEqual(response.status_code, 302)
        boss = User.objects.create_superuser("5012183813", PASSWORD, name="Boss")
        self.client.force_login(boss)
        self.assertEqual(self.client.get(f"/{settings.DJANGO_ADMIN_PATH}").status_code, 200)


class StoreTests(ConsoleCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.admin)

    def test_list_counts_and_search(self):
        Vendor.objects.create(owner=self.owner, name="Basra Fish", location=BAGHDAD)
        data = self.client.get("/api/console/stores/?status=pending").json()
        self.assertEqual([s["name"] for s in data["results"]], ["Basra Fish"])
        self.assertEqual(data["counts"], {"pending": 1, "approved": 1, "rejected": 0})
        self.assertEqual(len(self.client.get("/api/console/stores/?q=tigris").json()["results"]), 1)

    def test_create_a_store_with_a_new_owner(self):
        response = self.post(
            "/api/console/stores/",
            {"name": "Erbil Bakery", "latitude": 36.19, "longitude": 44.01, "owner_phone": "0781 222 3344", "owner_name": "Hawre"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        store = Vendor.objects.get(name="Erbil Bakery")
        self.assertEqual(store.status, Vendor.Status.APPROVED)
        self.assertEqual(store.owner.phone, "+9647812223344")
        self.assertEqual(store.owner.role, User.Role.VENDOR)
        self.assertTrue(AuditEntry.objects.filter(action="store.create").exists())

    def test_a_captain_cant_become_an_owner(self):
        response = self.post(
            "/api/console/stores/", {"name": "X", "latitude": 33, "longitude": 44, "owner_phone": "07500000992"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("owner_phone", response.json())

    def test_review_an_application(self):
        pending = Vendor.objects.create(owner=self.owner, name="Basra Fish", location=BAGHDAD)
        url = f"/api/console/stores/{pending.pk}/review/"
        self.assertEqual(self.post(url, {"decision": "reject"}).status_code, 400)
        self.post(url, {"decision": "reject", "reason": "Menu photos missing"})
        pending.refresh_from_db()
        self.assertEqual(pending.status, Vendor.Status.REJECTED)
        self.assertEqual(pending.reviewed_by, self.admin.user)

        self.post(url, {"decision": "approve", "commission_rate": "12"})
        pending.refresh_from_db()
        self.assertEqual((pending.status, pending.commission_rate, pending.rejection_reason), ("approved", Decimal("12"), ""))
        self.assertEqual(AuditEntry.objects.filter(target_type="vendor", target_id=str(pending.pk)).count(), 2)

    def test_edit_records_what_changed(self):
        self.patch(f"/api/console/stores/{self.store.pk}/", {"commission_rate": "10", "is_open": False})
        self.store.refresh_from_db()
        self.assertEqual(self.store.commission_rate, Decimal("10"))
        entry = AuditEntry.objects.get(action="store.update")
        self.assertEqual(entry.changes["commission_rate"], ["15.00", "10.00"])
        self.assertEqual(entry.actor_email, "admin@wasel.iq")

    def test_menu_and_team(self):
        url = f"/api/console/stores/{self.store.pk}/menu/"
        product = self.post(url, {"name_ar": "كباب", "price": "6000"}).json()
        self.assertEqual(self.client.get(url).json()[0]["name_ar"], "كباب")
        self.assertEqual(self.post(url, {"name_ar": "x", "price": "0"}).status_code, 400)
        self.client.delete(f"/api/console/products/{product['id']}/")
        self.assertFalse(Product.objects.filter(pk=product["id"]).exists())

        team = f"/api/console/stores/{self.store.pk}/team/"
        member = self.post(team, {"phone": "07801112233", "role": "manager"}).json()
        self.assertEqual(StoreMember.objects.get(pk=member["id"]).role, "manager")
        self.assertEqual(self.post(team, {"phone": "07801112233"}).json()["error"], "already_member")
        self.patch(f"{team}{member['id']}/", {"role": "cashier"})
        self.assertEqual(StoreMember.objects.get(pk=member["id"]).role, "cashier")
        self.client.delete(f"{team}{member['id']}/")
        self.assertFalse(StoreMember.objects.exists())


class OrderTests(ConsoleCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.admin)

    def test_live_and_all_orders(self):
        live = self.order()
        self.order(Order.Status.DELIVERED)
        StuckOrderAlert.objects.create(order=live, reason=StuckOrderAlert.Reason.NOT_ACCEPTED)
        data = self.client.get("/api/console/orders/").json()
        self.assertEqual([o["id"] for o in data["results"]], [live.pk])
        self.assertEqual(data["results"][0]["alerts"], ["not_accepted"])
        self.assertEqual(self.client.get("/api/console/orders/?scope=all").json()["count"], 2)
        self.assertEqual(self.client.get(f"/api/console/orders/?scope=all&q=%23{live.pk}").json()["count"], 1)

    def test_support_cancels_and_refunds_a_wallet_order(self):
        order = self.order(Order.Status.PREPARING, payment_type=Order.PaymentType.WALLET, payment_status=Order.PaymentStatus.PAID)
        alert = StuckOrderAlert.objects.create(order=order, reason=StuckOrderAlert.Reason.NOT_READY)
        self.sign_in(self.staff("support"))
        self.assertEqual(self.post(f"/api/console/orders/{order.pk}/cancel/").status_code, 400)
        response = self.post(f"/api/console/orders/{order.pk}/cancel/", {"reason": "Store closed early"})
        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertEqual((order.status, order.cancelled_by, order.payment_status), ("cancelled", "support", "refunded"))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.wallet_balance, 10000)
        alert.refresh_from_db()
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(self.post(f"/api/console/orders/{order.pk}/cancel/", {"reason": "again"}).status_code, 409)

    def test_release_a_captain(self):
        order = self.order(Order.Status.READY, captain=self.captain)
        response = self.post(f"/api/console/orders/{order.pk}/release/", {"reason": "Bike broke down"})
        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertIsNone(order.captain_id)
        self.assertTrue(response.json()["can_dispatch"])

    def test_dispatch_offers_to_the_nearest_captain(self):
        order = self.order(Order.Status.PREPARING)
        CaptainLocation.objects.create(captain=self.captain, point=BAGHDAD, is_online=True, updated_at=timezone.now())
        response = self.post(f"/api/console/orders/{order.pk}/dispatch/")
        self.assertTrue(response.json()["offered"])
        self.assertEqual(DispatchOffer.objects.get().captain, self.captain)

    def test_detail_and_overview(self):
        order = self.order(Order.Status.DELIVERED)
        Order.objects.filter(pk=order.pk).update(delivered_at=order.created_at + timedelta(minutes=25))
        detail = self.client.get(f"/api/console/orders/{order.pk}/").json()
        self.assertEqual([t["step"] for t in detail["timeline"]], ["received", "delivered"])
        overview = self.client.get("/api/console/overview/").json()
        self.assertEqual(overview["today"]["sales"], "10000")
        self.assertEqual(len(overview["days"]), 14)
        self.assertEqual(overview["days"][-1]["orders"], 1)


class PeopleTests(ConsoleCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.admin)

    def test_users_skip_staff_and_block(self):
        data = self.client.get("/api/console/users/").json()
        self.assertNotIn(self.admin.user_id, [u["id"] for u in data["results"]])
        self.assertEqual(data["counts"]["captain"], 1)
        self.post(f"/api/console/users/{self.captain.pk}/active/", {"is_active": False, "reason": "Fraud"})
        self.captain.refresh_from_db()
        self.assertFalse(self.captain.is_active)
        self.assertEqual(self.post(f"/api/console/users/{self.admin.user_id}/active/", {"is_active": False}).status_code, 404)

    def test_wallet_adjustments(self):
        url = f"/api/console/users/{self.customer.pk}/wallet/"
        self.assertEqual(self.post(url, {"amount": 5000}).status_code, 400)  # no reason
        self.assertEqual(self.post(url, {"amount": 5000, "reason": "Late order"}).json()["wallet_balance"], "5000")
        self.assertEqual(self.post(url, {"amount": -6000, "reason": "Typo"}).json()["error"], "insufficient_balance")
        self.assertEqual(WalletTransaction.objects.get().type, "adjustment")
        self.assertEqual(AuditEntry.objects.get(action="wallet.adjust").changes["reason"], "Late order")
        # Support can see people but not move money.
        self.sign_in(self.staff("support"))
        self.assertEqual(self.post(url, {"amount": 100, "reason": "x"}).status_code, 403)

    def test_staff_management_guards(self):
        response = self.post(
            "/api/console/staff/", {"email": "Sara@Wasel.iq", "name": "Sara", "role": "support", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 201, response.content)
        sara = StaffProfile.objects.get(email="sara@wasel.iq")
        self.assertTrue(sara.user.is_staff)
        self.assertFalse(sara.user.is_superuser)
        self.assertEqual(self.post("/api/console/staff/", {"email": "x@wasel.iq", "name": "X", "role": "support", "password": "short"}).status_code, 400)

        self.assertEqual(self.patch(f"/api/console/staff/{self.admin.pk}/", {"role": "support"}).json()["error"], "self_lockout")
        self.patch(f"/api/console/staff/{sara.pk}/", {"role": "finance"})
        sara.refresh_from_db()
        self.assertEqual(sara.role, "finance")

        sara.totp_enabled, sara.totp_secret = True, totp.new_secret()
        sara.save()
        self.post(f"/api/console/staff/{sara.pk}/reset/", {"what": "two_factor"})
        sara.refresh_from_db()
        self.assertFalse(sara.totp_enabled)

    def test_keep_one_admin(self):
        other = self.staff("admin", "second@wasel.iq")
        self.sign_in(other)
        self.patch(f"/api/console/staff/{self.admin.pk}/", {"is_active": False})
        response = self.patch(f"/api/console/staff/{self.admin.pk}/", {"is_active": True})
        self.assertEqual(response.status_code, 200)
        self.patch(f"/api/console/staff/{self.admin.pk}/", {"role": "support"})
        # Now `other` is the last admin and can't demote themself either.
        self.assertEqual(self.patch(f"/api/console/staff/{other.pk}/", {"role": "support"}).status_code, 400)

    def test_audit_log_search(self):
        self.patch(f"/api/console/stores/{self.store.pk}/", {"name": "Tigris Grill 2"})
        data = self.client.get("/api/console/audit/?action=store").json()
        self.assertEqual(data["results"][0]["summary"], "Edited store Tigris Grill 2")


class MoneyTests(ConsoleCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.staff("finance"))

    def test_payouts(self):
        today = timezone.localdate()
        statement = Statement.objects.create(
            vendor=self.store, period_start=today - timedelta(days=13), period_end=today - timedelta(days=7), payout=50000
        )
        data = self.client.get("/api/console/payouts/?status=due").json()
        self.assertEqual((data["due_total"], data["count"]), ("50000", 1))
        self.post(f"/api/console/payouts/{statement.pk}/paid/", {"reference": "TRX-9"})
        statement.refresh_from_db()
        self.assertEqual((statement.status, statement.paid_reference), ("paid", "TRX-9"))
        self.assertEqual(self.post(f"/api/console/payouts/{statement.pk}/paid/").status_code, 400)

    def test_reports(self):
        self.order(Order.Status.DELIVERED)
        self.order(Order.Status.CANCELLED, cancelled_by="vendor")
        data = self.client.get("/api/console/reports/").json()
        self.assertEqual(len(data["days"]), 30)
        self.assertEqual(data["totals"]["sales"], "10000")
        self.assertEqual(data["stores"][0]["name"], "Tigris Grill")
        self.assertEqual(data["cancelled_by"], {"vendor": 1})


class MarketingTests(ConsoleCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.staff("marketing"))

    def test_offers(self):
        now = timezone.now()
        bad = self.post("/api/console/offers/", {"title": "x", "type": "percent", "value": "150", "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat()})
        self.assertEqual(bad.status_code, 400)
        offer = self.post(
            "/api/console/offers/",
            {"title": "Ramadan 20%", "type": "percent", "value": "20", "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=7)).isoformat(), "is_banner": True},
        ).json()
        self.assertEqual(offer["state"], "running")
        self.assertIsNone(offer["store"])
        self.assertEqual(self.client.get("/api/console/offers/?state=running").json()["count"], 1)

        used = Offer.objects.get(pk=offer["id"])
        self.order(offer=used)
        self.client.delete(f"/api/console/offers/{used.pk}/")
        used.refresh_from_db()
        self.assertLessEqual(used.ends_at, timezone.now())
