"""
Store owners sign themselves up, Wasel staff approve or reject the store,
approved owners add branches, and team members join by accepting invites.
"""

from decimal import Decimal

from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from orders.models import Order
from subscriptions.models import WaselPlusSubscription
from subscriptions.services import start_wasel_plus_trial

from .models import Product, StoreInvite, StoreMember, Vendor

BAGHDAD = Point(44.4214, 33.3045, srid=4326)

APPLICATION = {
    "owner_name": "Hassan Ali",
    "name": "Hassan's Grill",
    "type": "restaurant",
    "cuisine": "eastern",
    "address": "Karrada, street 62, near the bridge",
    "latitude": 33.3045,
    "longitude": 44.4214,
    "delivery_radius_km": "6",
}


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def new_number(phone="+9647800000501"):
    """What verifying a login code makes for a number Wasel hasn't seen."""
    user = User.objects.create_user(phone)
    start_wasel_plus_trial(user)
    return user


class ApplyTests(TestCase):
    def test_a_new_number_applies_and_waits_for_approval(self):
        user = new_number()
        client = client_for(user)
        before = client.get("/api/store-applications/").data
        self.assertEqual((before["can_apply"], before["applications"]), (True, []))

        response = client.post("/api/store-applications/", APPLICATION, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "pending")

        user.refresh_from_db()
        self.assertEqual((user.role, user.name), (User.Role.VENDOR, "Hassan Ali"))
        # The free trial was for customers.
        self.assertFalse(WaselPlusSubscription.objects.filter(user=user, status="trial").exists())

        store = Vendor.objects.get(owner=user)
        self.assertEqual(store.status, Vendor.Status.PENDING)
        self.assertEqual((store.address, store.delivery_radius_km), (APPLICATION["address"], Decimal("6")))
        self.assertAlmostEqual(store.location.y, 33.3045)

        after = client.get("/api/store-applications/").data
        self.assertEqual((after["can_apply"], after["reason"]), (False, "application_pending"))
        self.assertEqual([a["name"] for a in after["applications"]], ["Hassan's Grill"])
        # Not a store to run yet.
        self.assertEqual(client.get("/api/vendors/mine/").data, [])
        refused = client.post("/api/store-applications/", APPLICATION, format="json")
        self.assertEqual(refused.data["error"], "application_pending")

    def test_supermarkets_have_no_cuisine_and_bad_input_is_explained(self):
        client = client_for(new_number())
        response = client.post(
            "/api/store-applications/", {**APPLICATION, "type": "supermarket", "cuisine": "eastern"}, format="json"
        )
        self.assertEqual(response.data["cuisine"], "")

        client = client_for(new_number("+9647800000502"))
        response = client.post(
            "/api/store-applications/",
            {**APPLICATION, "owner_name": "", "name": " ", "latitude": 51.5, "delivery_radius_km": "80"},
            format="json",
        )
        self.assertEqual(response.data["error"], "invalid_application")
        self.assertEqual(set(response.data["detail"]), {"name", "latitude", "delivery_radius_km"})
        response = client.post("/api/store-applications/", {**APPLICATION, "owner_name": ""}, format="json")
        self.assertIn("owner_name", response.data["detail"])

    def test_customers_with_history_captains_and_staff_cant_apply(self):
        owner = User.objects.create_user("+9647800000503", role=User.Role.VENDOR)
        store = Vendor.objects.create(owner=owner, name="Old", location=BAGHDAD, status=Vendor.Status.APPROVED)
        customer = User.objects.create_user("+9647700000504", name="Zainab")
        Order.objects.create(customer=customer, vendor=store, delivery_address="x", delivery_location=BAGHDAD)
        captain = User.objects.create_user("+9647500000505", role=User.Role.CAPTAIN, name="Ahmed")
        staff = User.objects.create_user("+9647800000506", password="x", is_staff=True, name="Staff")
        for user in (customer, captain, staff):
            client = client_for(user)
            self.assertEqual(client.get("/api/store-applications/").data["reason"], "phone_in_use")
            response = client.post("/api/store-applications/", APPLICATION, format="json")
            self.assertEqual(response.data["error"], "phone_in_use", user)
        self.assertEqual(Vendor.objects.count(), 1)
        customer.refresh_from_db()
        self.assertEqual(customer.role, User.Role.CUSTOMER)

    def test_the_owner_can_t_be_chosen(self):
        other = User.objects.create_user("+9647800000507", role=User.Role.VENDOR)
        user = new_number()
        client_for(user).post("/api/store-applications/", {**APPLICATION, "owner": other.pk}, format="json")
        self.assertEqual(Vendor.objects.get().owner, user)


class CustomersNeverSeeUnapprovedStoresTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("+9647800000510", role=User.Role.VENDOR)
        self.customer = User.objects.create_user("+9647700000511")
        self.stores = {}
        for status in Vendor.Status.values:
            store = Vendor.objects.create(owner=self.owner, name=status, location=BAGHDAD, is_open=True, status=status)
            Product.objects.create(vendor=store, name_ar="كباب", price=9000)
            self.stores[status] = store

    def test_lists_details_quotes_and_orders(self):
        client = client_for(self.customer)
        listed = client.get("/api/vendors/?lat=33.3045&lng=44.4214").data
        names = [v["name"] for v in (listed["results"] if isinstance(listed, dict) else listed)]
        self.assertEqual(names, ["approved"])
        for status in ("pending", "rejected"):
            store = self.stores[status]
            self.assertEqual(client.get(f"/api/vendors/{store.pk}/").status_code, 404)
            cart = {
                "vendor": store.pk,
                "items": [{"product": store.products.get().pk, "quantity": "1"}],
                "delivery_latitude": 33.3045,
                "delivery_longitude": 44.4214,
                "delivery_address": "Karrada",
                "payment_type": "cod",
            }
            self.assertEqual(client.post("/api/orders/quote/", cart, format="json").data["error"], "vendor_not_found")
            self.assertEqual(client.post("/api/orders/", cart, format="json").data["error"], "vendor_not_found")
        self.assertFalse(Order.objects.exists())

    def test_the_owner_can_t_open_or_run_a_store_before_approval(self):
        client = client_for(self.owner)
        pending = self.stores["pending"]
        self.assertEqual([s["name"] for s in client.get("/api/vendors/mine/").data], ["approved"])
        self.assertEqual(client.post(f"/api/vendors/{pending.pk}/open/", {"is_open": True}).status_code, 404)
        self.assertEqual(client.post(f"/api/vendors/{pending.pk}/products/", {"name_ar": "x", "price": 1}).status_code, 403)
        self.assertEqual(client.get(f"/api/vendors/{pending.pk}/team/").status_code, 403)
        # ...but sees all three as applications.
        apps = client.get("/api/store-applications/").data["applications"]
        self.assertEqual(sorted(a["status"] for a in apps), ["approved", "pending", "rejected"])


class ReviewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("+9647800000520", password="x", is_staff=True, name="Noor")
        self.ops = APIClient()
        self.ops.force_login(self.staff)
        self.owner = new_number("+9647800000521")
        client_for(self.owner).post("/api/store-applications/", APPLICATION, format="json")
        self.store = Vendor.objects.get(owner=self.owner)

    def test_staff_list_pending_applications(self):
        data = self.ops.get("/api/ops/applications/").data
        self.assertEqual(data["counts"]["pending"], 1)
        row = data["results"][0]
        self.assertEqual((row["name"], row["owner"]["phone"], row["new_branch"]), ("Hassan's Grill", "+9647800000521", False))
        self.assertEqual(self.ops.get("/api/ops/overview/").data["live"]["applications"], 1)
        # Not among the running stores yet.
        self.assertEqual(self.ops.get("/api/ops/stores/").data, [])

    def test_approving_sets_commission_and_the_owner_sees_it(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.ops.post(f"/api/ops/applications/{self.store.pk}/approve/", {"commission_rate": "12.5"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.store.refresh_from_db()
        self.assertEqual((self.store.status, self.store.commission_rate), (Vendor.Status.APPROVED, Decimal("12.5")))
        self.assertEqual(self.store.reviewed_by, self.staff)

        owner = client_for(self.owner)
        mine = owner.get("/api/vendors/mine/").data
        self.assertEqual((mine[0]["id"], mine[0]["my_role"]), (self.store.pk, "owner"))
        self.assertEqual(APIClient().get(f"/api/vendors/{self.store.pk}/").status_code, 200)
        # Approved owners may add branches.
        self.assertTrue(owner.get("/api/store-applications/").data["can_apply"])

        again = self.ops.post(f"/api/ops/applications/{self.store.pk}/approve/", {}, format="json")
        self.assertEqual(again.data["error"], "already_reviewed")

    def test_commission_defaults_to_15_percent(self):
        self.store.commission_rate = Decimal("20")
        self.store.save()
        self.ops.post(f"/api/ops/applications/{self.store.pk}/approve/", {}, format="json")
        self.store.refresh_from_db()
        self.assertEqual(self.store.commission_rate, Decimal("15"))

    def test_rejecting_needs_a_reason_the_owner_then_sees(self):
        self.assertEqual(self.ops.post(f"/api/ops/applications/{self.store.pk}/reject/", {"reason": " "}, format="json").status_code, 400)
        response = self.ops.post(
            f"/api/ops/applications/{self.store.pk}/reject/", {"reason": "The address couldn't be found."}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        apps = client_for(self.owner).get("/api/store-applications/").data
        self.assertEqual(apps["applications"][0]["status"], "rejected")
        self.assertEqual(apps["applications"][0]["rejection_reason"], "The address couldn't be found.")
        self.assertEqual(apps["applications"][0]["rejection_reason"], "The address couldn't be found.")
        # They can fix it and apply again.
        self.assertTrue(apps["can_apply"])
        self.assertEqual(self.ops.get("/api/ops/applications/?status=rejected").data["results"][0]["id"], self.store.pk)

    def test_only_staff_review(self):
        for user in (self.owner, User.objects.create_user("+9647700000522")):
            client = APIClient()
            client.force_login(user)
            self.assertEqual(client.get("/api/ops/applications/").status_code, 403)
            self.assertEqual(client.post(f"/api/ops/applications/{self.store.pk}/approve/", {}).status_code, 403)
            self.assertEqual(client.post(f"/api/ops/applications/{self.store.pk}/reject/", {"reason": "x"}).status_code, 403)
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Vendor.Status.PENDING)


class BranchTests(TestCase):
    def test_an_approved_owner_adds_branches_that_wait_for_approval(self):
        owner = User.objects.create_user("+9647800000530", role=User.Role.VENDOR, name="Hassan")
        Vendor.objects.create(owner=owner, name="Main", location=BAGHDAD, status=Vendor.Status.APPROVED)
        client = client_for(owner)
        for n in range(3):
            response = client.post("/api/store-applications/", {**APPLICATION, "owner_name": "", "name": f"Branch {n}"}, format="json")
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(client.post("/api/store-applications/", APPLICATION, format="json").data["error"], "too_many_applications")
        self.assertEqual([s["name"] for s in client.get("/api/vendors/mine/").data], ["Main"])

        ops = APIClient()
        ops.force_login(User.objects.create_user("+9647800000531", password="x", is_staff=True))
        self.assertTrue(ops.get("/api/ops/applications/").data["results"][0]["new_branch"])
        owner.refresh_from_db()
        self.assertEqual(owner.name, "Hassan")


class InviteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("+9647800000540", role=User.Role.VENDOR, name="Owner")
        self.store = Vendor.objects.create(owner=self.owner, name="Tigris Grill", location=BAGHDAD, status=Vendor.Status.APPROVED)
        self.owner_client = client_for(self.owner)

    def invite(self, phone="07800000541", role="manager", name="Sara"):
        return self.owner_client.post(
            f"/api/vendors/{self.store.pk}/team/", {"phone": phone, "role": role, "name": name}, format="json"
        )

    def test_people_with_an_account_see_the_invite_when_they_sign_in(self):
        sara = User.objects.create_user("+9647800000541", role=User.Role.VENDOR)
        invite = self.invite().data
        mine = client_for(sara).get("/api/store-invites/").data
        self.assertEqual([i["id"] for i in mine], [invite["id"]])

    def test_declining_leaves_the_team_unchanged(self):
        self.invite()
        sara = User.objects.create_user("+9647800000541", role=User.Role.VENDOR)
        client = client_for(sara)
        invite = client.get("/api/store-invites/").data[0]
        self.assertEqual((invite["role"], invite["invited_by"]), ("manager", "Owner"))
        self.assertEqual(client.post(f"/api/store-invites/{invite['id']}/decline/").data["status"], "declined")
        self.assertEqual(client.get("/api/store-invites/").data, [])
        self.assertFalse(StoreMember.objects.exists())
        # Answered invites can't be answered again.
        self.assertEqual(client.post(f"/api/store-invites/{invite['id']}/accept/").status_code, 404)
        # The owner may ask again.
        self.assertEqual(self.invite().status_code, 201)

    def test_the_owner_cancels_an_invite(self):
        invite = self.invite().data
        self.assertEqual(self.owner_client.delete(f"/api/vendors/{self.store.pk}/team/invites/{invite['id']}/").status_code, 204)
        self.assertEqual(self.owner_client.get(f"/api/vendors/{self.store.pk}/team/").data["invites"], [])
        sara = User.objects.create_user("+9647800000541", role=User.Role.VENDOR)
        self.assertEqual(client_for(sara).get("/api/store-invites/").data, [])
        self.assertEqual(client_for(sara).post(f"/api/store-invites/{invite['id']}/accept/").status_code, 404)

    def test_an_invite_is_only_for_its_own_number(self):
        invite = self.invite().data
        stranger = User.objects.create_user("+9647800000549", role=User.Role.VENDOR)
        client = client_for(stranger)
        self.assertEqual(client.get("/api/store-invites/").data, [])
        self.assertEqual(client.post(f"/api/store-invites/{invite['id']}/accept/").status_code, 404)
        self.assertFalse(StoreMember.objects.exists())
        self.assertEqual(StoreInvite.objects.get().status, StoreInvite.Status.PENDING)

    def test_a_customer_who_ordered_since_being_invited_can_t_accept(self):
        self.invite()
        sara = User.objects.create_user("+9647800000541")
        Order.objects.create(customer=sara, vendor=self.store, delivery_address="x", delivery_location=BAGHDAD)
        client = client_for(sara)
        invite = client.get("/api/store-invites/").data[0]
        self.assertEqual(client.post(f"/api/store-invites/{invite['id']}/accept/").data["error"], "phone_in_use")
        sara.refresh_from_db()
        self.assertEqual(sara.role, User.Role.CUSTOMER)

    def test_managers_and_cashiers_can_t_invite(self):
        cashier = User.objects.create_user("+9647800000543", role=User.Role.VENDOR)
        StoreMember.objects.create(vendor=self.store, user=cashier, role="manager")
        response = client_for(cashier).post(f"/api/vendors/{self.store.pk}/team/", {"phone": "07800000544"}, format="json")
        self.assertEqual(response.status_code, 403)
