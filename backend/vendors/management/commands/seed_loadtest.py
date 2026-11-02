"""
Fill a load-test database: stores with menus around Baghdad, and customers,
captains and store owners who are already signed in. Writes their tokens and
ids to a JSON file for the k6 script (deploy/loadtest/).

Refuses to run unless LOADTEST=1, so it can't touch a real database.
"""

import json
import os
import random
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AuthToken, User
from orders.models import Order
from vendors.models import Product, ProductModifier, Vendor
from vendors.search import refresh_search_text

# Karrada, Baghdad.
CENTRE = (33.3070, 44.4200)
CUISINES = ["eastern", "western", "fast_food", "sweets", "drinks", "popular"]
TYPES = ["restaurant"] * 6 + ["supermarket", "cafe", "pharmacy", "convenience", "flowers"]
DISHES = ["كباب", "تكة", "برغر", "شاورما", "بيتزا", "دولمة", "قوزي", "فلافل", "سمك مسكوف", "كبة", "باجة", "بامية"]


def near(km):
    """A random spot within `km` of the centre (roughly; 1 degree ≈ 111 km)."""
    lat, lng = CENTRE
    return lat + random.uniform(-km, km) / 111, lng + random.uniform(-km, km) / 93


class Command(BaseCommand):
    help = "Create load-test stores, menus and signed-in users (LOADTEST=1 only)."

    def add_arguments(self, parser):
        parser.add_argument("--stores", type=int, default=200)
        parser.add_argument("--products", type=int, default=25, help="per store")
        parser.add_argument("--customers", type=int, default=3000)
        parser.add_argument("--captains", type=int, default=500)
        parser.add_argument("--out", default="/loadtest/data.json")

    @transaction.atomic
    def handle(self, *args, stores, products, customers, captains, out, **options):
        if os.environ.get("LOADTEST") != "1":
            raise CommandError("Only for the load-test stack: set LOADTEST=1.")
        random.seed(7)
        unusable = make_password(None)

        def users(prefix, count, role):
            created = User.objects.bulk_create(
                [
                    User(phone=f"+96477{prefix}{i:05d}", role=role, password=unusable, name=f"LT {role} {i}")
                    for i in range(count)
                ],
                ignore_conflicts=True,
            )
            rows = list(User.objects.filter(phone__startswith=f"+96477{prefix}").order_by("phone"))
            AuthToken.objects.filter(user__in=rows).delete()
            tokens = AuthToken.objects.bulk_create([AuthToken(user=u, key=os.urandom(20).hex()) for u in rows])
            return [{"id": t.user_id, "token": t.key} for t in tokens], len(created)

        customer_rows, _ = users("1", customers, User.Role.CUSTOMER)
        captain_rows, _ = users("2", captains, User.Role.CAPTAIN)
        owner_rows, _ = users("3", stores, User.Role.VENDOR)

        # Every run starts from the same data: earlier runs' orders go first (they protect their stores).
        Order.objects.filter(vendor__name__startswith="LT ").delete()
        Vendor.objects.filter(name__startswith="LT ").delete()
        vendors = Vendor.objects.bulk_create(
            [
                Vendor(
                    owner_id=owner["id"],
                    name=f"LT {DISHES[i % len(DISHES)]} {i}",
                    status=Vendor.Status.APPROVED,
                    type=(kind := TYPES[i % len(TYPES)]),
                    cuisine=CUISINES[i % len(CUISINES)] if kind == "restaurant" else "",
                    location=Point(*reversed(near(7)), srid=4326),
                    delivery_radius_km=Decimal("10"),
                    is_open=True,
                    commission_rate=Decimal("15"),
                )
                for i, owner in enumerate(owner_rows)
            ]
        )
        items = Product.objects.bulk_create(
            [
                Product(
                    vendor=vendor,
                    name_ar=f"{DISHES[j % len(DISHES)]} {j}",
                    name_en=f"Dish {j}",
                    description_ar="لحم مشوي على الفحم مع خبز وسلطة",
                    menu_section=["مشويات", "سندويشات", "مشروبات", "حلويات"][j % 4],
                    price=Decimal(random.choice([1500, 3000, 5000, 7000, 9000, 12000])),
                )
                for vendor in vendors
                for j in range(products)
            ]
        )
        # A size choice on every fifth item, like real menus.
        ProductModifier.objects.bulk_create(
            [
                ProductModifier(product=p, group_name="الحجم", name_ar=size, price_delta=delta, is_required=True)
                for p in items[::5]
                for size, delta in (("عادي", 0), ("كبير", 2000))
            ]
        )

        refresh_search_text(v.pk for v in vendors)

        menu = {}
        for p in items:
            menu.setdefault(p.vendor_id, []).append(p.pk)
        sized = {p.pk for p in items[::5]}
        data = {
            "centre": {"lat": CENTRE[0], "lng": CENTRE[1]},
            "customers": customer_rows,
            "captains": captain_rows,
            "stores": [
                {"id": v.pk, "token": owner["token"], "products": [pk for pk in menu[v.pk] if pk not in sized]}
                for v, owner in zip(vendors, owner_rows)
            ],
        }
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            json.dump(data, f)
        self.stdout.write(
            f"{len(vendors)} stores, {len(items)} items, {len(customer_rows)} customers, "
            f"{len(captain_rows)} captains -> {out}"
        )
