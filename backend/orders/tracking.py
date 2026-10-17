"""
Live captain tracking.

Captains send their position every few seconds (over their socket, or by
REST when the app is in the background). The latest position is saved and
pushed to the customer and the store of every order the captain is on,
from claim until delivery. Nobody sees a captain's position outside an
active order.
"""

from datetime import timedelta

from django.contrib.gis.geos import Point
from django.utils import timezone

from . import realtime
from .models import TRACKED_STATUSES, CaptainLocation, Order
from .serializers import location_payload

# Updates closer together than this are dropped, to spare the database and the apps.
MIN_INTERVAL = timedelta(seconds=2)


def update_captain_location(captain, lat, lng, heading=None, speed=None):
    """Save the captain's position and push it to their active orders. Returns False if throttled."""
    now = timezone.now()
    last = CaptainLocation.objects.filter(captain=captain).values_list("updated_at", flat=True).first()
    if last and now - last < MIN_INTERVAL:
        return False

    location, _ = CaptainLocation.objects.update_or_create(
        captain=captain,
        defaults={"point": Point(lng, lat, srid=4326), "heading": heading, "speed": speed, "updated_at": now},
    )
    payload = location_payload(location)
    for order_id, customer_id, vendor_id in Order.objects.filter(
        captain=captain, status__in=TRACKED_STATUSES
    ).values_list("pk", "customer_id", "vendor_id"):
        realtime.send_captain_location(order_id, customer_id, vendor_id, payload)
    return True
