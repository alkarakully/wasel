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
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import realtime
from .models import TRACKED_STATUSES, CaptainLocation, Order
from .serializers import location_payload

# Updates closer together than this are dropped, to spare the database and the apps.
MIN_INTERVAL = timedelta(seconds=2)


def update_captain_location(captain, lat, lng, heading=None, speed=None):
    """Save the captain's position and push it to their active orders. Returns False if throttled."""
    now = timezone.now()
    fields = {"point": Point(lng, lat, srid=4326), "heading": heading, "speed": speed, "updated_at": now}
    # One UPDATE does the throttle and the save: it only touches a position older
    # than MIN_INTERVAL. This runs for every captain every few seconds, the most
    # frequent write Wasel has.
    saved = CaptainLocation.objects.filter(captain=captain, updated_at__lte=now - MIN_INTERVAL).update(**fields)
    if not saved:
        if CaptainLocation.objects.filter(captain=captain).exists():
            return False  # too soon after the last one
        try:
            with transaction.atomic():
                CaptainLocation.objects.create(captain=captain, **fields)
        except IntegrityError:
            return False  # another update made the first row at the same moment

    payload = location_payload(CaptainLocation(captain=captain, **fields))
    for order_id, customer_id, vendor_id in Order.objects.filter(
        captain=captain, status__in=TRACKED_STATUSES
    ).values_list("pk", "customer_id", "vendor_id"):
        realtime.send_captain_location(order_id, customer_id, vendor_id, payload)
    return True
