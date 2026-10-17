from datetime import timedelta
from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from vendors.models import Vendor

from .models import Order, StuckOrderAlert
from .tasks import flag_stuck_orders

BAGHDAD = Point(44.4009, 33.3406, srid=4326)
Reason = StuckOrderAlert.Reason


@mock.patch("orders.tasks.send_stuck_alert")
class StuckOrderTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000060")
        self.captain = User.objects.create_user(phone="+9647500000061", role=User.Role.CAPTAIN)
        owner = User.objects.create_user(phone="+9647800000062", role=User.Role.VENDOR)
        self.vendor = Vendor.objects.create(owner=owner, name="Slow Grill", location=BAGHDAD, is_open=True)
        self.now = timezone.now()

    def order(self, minutes_old=0, **fields):
        order = Order.objects.create(
            customer=self.customer, vendor=self.vendor, delivery_address="Karrada", delivery_location=BAGHDAD, **fields
        )
        Order.objects.filter(pk=order.pk).update(created_at=self.now - timedelta(minutes=minutes_old))
        return order

    def ago(self, minutes):
        return self.now - timedelta(minutes=minutes)

    def open_alerts(self):
        return set(StuckOrderAlert.objects.filter(resolved_at__isnull=True).values_list("order_id", "reason"))

    def test_flags_each_kind_of_stuck_order(self, send):
        not_accepted = self.order(minutes_old=6)
        not_ready = self.order(status="preparing", captain=self.captain, accepted_at=self.ago(40), estimated_ready_at=self.ago(16))
        no_captain = self.order(status="ready", accepted_at=self.ago(11), estimated_ready_at=self.now, ready_at=self.ago(1))
        not_picked_up = self.order(status="ready", captain=self.captain, accepted_at=self.ago(30), ready_at=self.ago(16))
        late = self.order(status="out_for_delivery", captain=self.captain, picked_up_at=self.ago(61))

        result = flag_stuck_orders()

        self.assertEqual(result, {"created": 5, "resolved": 0})
        self.assertEqual(
            self.open_alerts(),
            {
                (not_accepted.pk, Reason.NOT_ACCEPTED),
                (not_ready.pk, Reason.NOT_READY),
                (no_captain.pk, Reason.NO_CAPTAIN),
                (not_picked_up.pk, Reason.NOT_PICKED_UP),
                (late.pk, Reason.DELIVERY_LATE),
            },
        )
        self.assertEqual(send.call_count, 5)

    def test_orders_within_limits_are_left_alone(self, send):
        self.order(minutes_old=4)
        self.order(status="preparing", captain=self.captain, accepted_at=self.ago(5), estimated_ready_at=self.ago(14))
        self.order(status="out_for_delivery", captain=self.captain, picked_up_at=self.ago(59))
        self.order(status="delivered", minutes_old=600)
        self.assertEqual(flag_stuck_orders(), {"created": 0, "resolved": 0})
        send.assert_not_called()

    def test_running_again_does_not_duplicate_alerts(self, send):
        self.order(minutes_old=6)
        flag_stuck_orders()
        self.assertEqual(flag_stuck_orders(), {"created": 0, "resolved": 0})
        self.assertEqual(StuckOrderAlert.objects.count(), 1)
        self.assertEqual(send.call_count, 1)

    def test_alert_resolves_when_order_moves_on(self, send):
        order = self.order(minutes_old=6)
        flag_stuck_orders()
        Order.objects.filter(pk=order.pk).update(status="preparing", accepted_at=self.now, estimated_ready_at=self.now)

        self.assertEqual(flag_stuck_orders(), {"created": 0, "resolved": 1})
        alert = StuckOrderAlert.objects.get()
        self.assertIsNotNone(alert.resolved_at)

    def test_a_resolved_problem_can_alert_again(self, send):
        order = self.order(minutes_old=6)
        flag_stuck_orders()
        StuckOrderAlert.objects.update(resolved_at=self.now)
        flag_stuck_orders()
        self.assertEqual(StuckOrderAlert.objects.filter(order=order).count(), 2)
