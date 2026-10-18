from datetime import timedelta
from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from vendors.models import Product, Vendor

from .models import CaptainLocation, DispatchOffer, Order
from .tasks import sweep_dispatch_offers

STORE = (33.3406, 44.4009)
KM = 0.009  # about one kilometre of latitude


@mock.patch("orders.realtime._send")
class DispatchTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000090")
        self.owner = User.objects.create_user(phone="+9647800000091", role=User.Role.VENDOR)
        self.store = Vendor.objects.create(
            owner=self.owner, name="Dispatch Grill", location=Point(STORE[1], STORE[0], srid=4326), is_open=True
        )
        product = Product.objects.create(vendor=self.store, name_ar="تكة", price=8000)
        self.client = APIClient()
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/orders/",
            {
                "vendor": self.store.pk,
                "items": [{"product": product.pk}],
                "delivery_latitude": STORE[0] + KM,
                "delivery_longitude": STORE[1],
                "delivery_address": "Karrada",
            },
            format="json",
        )
        self.order_id = response.json()["id"]
        self.near = self.captain("+9647500000001", km=0.5)
        self.farther = self.captain("+9647500000002", km=1.5)

    def captain(self, phone, km, online=True, minutes_ago=0, role=User.Role.CAPTAIN):
        user = User.objects.create_user(phone=phone, role=role)
        CaptainLocation.objects.create(
            captain=user,
            point=Point(STORE[1], STORE[0] + km * KM, srid=4326),
            is_online=online,
            updated_at=timezone.now() - timedelta(minutes=minutes_ago),
        )
        return user

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def accept_order(self):
        response = self.as_user(self.owner).post(f"/api/orders/{self.order_id}/accept/", {"prep_minutes": 15}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

    def pending(self):
        return DispatchOffer.objects.filter(order_id=self.order_id, status="pending").first()

    def available_ids(self, captain):
        return [o["id"] for o in self.as_user(captain).get("/api/orders/available/").json()["results"]]

    # --- Choosing a captain ----------------------------------------------------

    def test_accepted_order_goes_to_nearest_captain_only(self, send):
        self.accept_order()
        offer = self.pending()
        self.assertEqual(offer.captain, self.near)
        self.assertAlmostEqual(offer.distance_m, 500, delta=30)
        # Hidden from everyone else while the offer runs.
        self.assertEqual(self.available_ids(self.farther), [])
        response = self.as_user(self.farther).post(f"/api/orders/{self.order_id}/claim/")
        self.assertEqual((response.status_code, response.json()["error"]), (409, "offered_to_another"))

    def test_skips_offline_stale_busy_distant_and_non_captains(self, send):
        User.objects.filter(pk__in=[self.near.pk, self.farther.pk]).delete()
        self.captain("+9647500000010", km=0.2, online=False)
        self.captain("+9647500000011", km=0.3, minutes_ago=30)
        self.captain("+9647500000012", km=8)
        self.captain("+9647700000013", km=0.1, role=User.Role.CUSTOMER)
        busy = self.captain("+9647500000014", km=0.4)
        other = Order.objects.get(pk=self.order_id)
        Order.objects.create(
            customer=self.customer, vendor=self.store, captain=busy, status=Order.Status.OUT_FOR_DELIVERY,
            delivery_address="x", delivery_location=other.delivery_location,
        )
        good = self.captain("+9647500000015", km=2)

        self.accept_order()
        self.assertEqual(self.pending().captain, good)

    def test_nobody_free_means_open_to_all(self, send):
        CaptainLocation.objects.update(is_online=False)
        self.accept_order()
        self.assertIsNone(self.pending())
        self.assertEqual(self.available_ids(self.near), [self.order_id])

    # --- Answers -----------------------------------------------------------------

    def test_captain_accepts_offer(self, send):
        self.accept_order()
        offer = self.as_user(self.near).get("/api/dispatch/offers/current/").json()
        self.assertEqual(offer["order"]["id"], self.order_id)

        response = self.as_user(self.near).post(f"/api/dispatch/offers/{offer['id']}/accept/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["captain"], self.near.pk)
        self.assertEqual(DispatchOffer.objects.get(pk=offer["id"]).status, "accepted")
        self.assertEqual(self.as_user(self.near).get("/api/dispatch/offers/current/").status_code, 204)

    def test_decline_moves_to_next_nearest_then_to_everyone(self, send):
        self.accept_order()
        first = self.pending()
        self.assertEqual(self.as_user(self.near).post(f"/api/dispatch/offers/{first.pk}/decline/").status_code, 204)
        second = self.pending()
        self.assertEqual(second.captain, self.farther)

        with self.captureOnCommitCallbacks(execute=True):
            self.as_user(self.farther).post(f"/api/dispatch/offers/{second.pk}/decline/")
        self.assertIsNone(self.pending())
        self.assertEqual(self.available_ids(self.near), [self.order_id])
        sent = [call.args[1]["type"] for call in send.call_args_list]
        self.assertIn("order.available", sent)

    def test_expired_offer_moves_on(self, send):
        self.accept_order()
        first = self.pending()
        DispatchOffer.objects.filter(pk=first.pk).update(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertEqual(sweep_dispatch_offers(), 1)
        first.refresh_from_db()
        self.assertEqual(first.status, "expired")
        self.assertEqual(self.pending().captain, self.farther)

        late = self.as_user(self.near).post(f"/api/dispatch/offers/{first.pk}/accept/")
        self.assertEqual((late.status_code, late.json()["error"]), (409, "offer_gone"))

    def test_cannot_answer_someone_elses_offer(self, send):
        self.accept_order()
        offer = self.pending()
        response = self.as_user(self.farther).post(f"/api/dispatch/offers/{offer.pk}/accept/")
        self.assertEqual(response.status_code, 409)

    def test_going_offline_passes_the_offer_on(self, send):
        self.accept_order()
        response = self.as_user(self.near).post("/api/captain/status/", {"online": False}, format="json")
        self.assertEqual(response.json(), {"online": False})
        self.assertEqual(self.pending().captain, self.farther)

    def test_cancelled_order_withdraws_offer(self, send):
        # Customers can only cancel before the store accepts; the store rejects after.
        self.accept_order()
        offer = self.pending()
        Order.objects.filter(pk=self.order_id).update(status=Order.Status.RECEIVED)
        self.as_user(self.owner).post(f"/api/orders/{self.order_id}/reject/", {"reason": "Closing"}, format="json")
        offer.refresh_from_db()
        self.assertEqual(offer.status, "cancelled")

    def test_status_endpoint_is_for_captains(self, send):
        response = self.as_user(self.customer).post("/api/captain/status/", {"online": True}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_going_online_without_gps_yet(self, send):
        newcomer = User.objects.create_user(phone="+9647500000020", role=User.Role.CAPTAIN)
        self.as_user(newcomer).post("/api/captain/status/", {"online": True}, format="json")
        location = CaptainLocation.objects.get(captain=newcomer)
        self.assertTrue(location.is_online)
        self.assertIsNone(location.point)
