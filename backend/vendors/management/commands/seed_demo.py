"""
Development data: a few stores around Karrada, Baghdad, with menus and an offer.

    docker compose run --rm web python manage.py seed_demo

Safe to run again: it replaces the demo stores it created before.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from vendors.models import Offer, Product, ProductModifier, Vendor

OWNER_PHONE = "+9647800000999"
CAPTAIN_PHONE = "+9647500000999"

# (name, cuisine, type, lat, lng, open, products)
# products: (section, name_ar, name_ku, name_en, price, unit, modifiers)
# modifiers: (group, name_ar, name_ku, name_en, price_delta, required)
STORES = [
    (
        "مطعم دجلة للمشويات",
        "eastern",
        "restaurant",
        33.3060,
        44.4190,
        True,
        [
            (
                "المشويات",
                "كباب عراقي",
                "کەبابی عێراقی",
                "Iraqi kebab",
                9000,
                "item",
                [
                    ("الحجم", "عادي", "ئاسایی", "Regular", 0, True),
                    ("الحجم", "كبير", "گەورە", "Large", 3000, True),
                    ("إضافات", "صمون حجري", "سەمونی بەردین", "Stone-baked samoon", 500, False),
                    ("إضافات", "طرشي", "تورشی", "Pickles", 250, False),
                ],
            ),
            ("المشويات", "تكة دجاج", "تکەی مریشک", "Chicken tikka", 8000, "item", [("إضافات", "صمون حجري", "سەمونی بەردین", "Stone-baked samoon", 500, False)]),
            ("الأطباق", "قوزي على تمن", "قۆزی لەگەڵ برنج", "Quzi with rice", 15000, "item", []),
            ("المشروبات", "لبن", "دۆ", "Laban", 1000, "item", []),
        ],
    ),
    (
        "برغر الكرادة",
        "fast_food",
        "restaurant",
        33.3020,
        44.4250,
        True,
        [
            (
                "برغر",
                "برغر كلاسيك",
                "بەرگەری کلاسیک",
                "Classic burger",
                7000,
                "item",
                [
                    ("الوجبة", "سندويش فقط", "تەنها سەندویچ", "Sandwich only", 0, True),
                    ("الوجبة", "وجبة مع بطاطا وبيبسي", "ژەم لەگەڵ پەتاتە و پیپسی", "Meal with fries and Pepsi", 3000, True),
                ],
            ),
            ("برغر", "برغر دجاج مقرمش", "بەرگەری مریشکی ترسکە", "Crispy chicken burger", 6500, "item", []),
            ("جانبي", "بطاطا مقلية", "پەتاتەی سوورکراو", "Fries", 2000, "item", []),
        ],
    ),
    (
        "حلويات بغداد",
        "sweets",
        "restaurant",
        33.3075,
        44.4280,
        True,
        [
            ("حلويات", "كليجة بالتمر", "کلێچەی خورما", "Date kleicha", 6000, "kg", []),
            ("حلويات", "زلابية", "زەلابیە", "Zalabia", 4000, "kg", []),
            ("مشروبات", "شاي عراقي", "چای عێراقی", "Iraqi tea", 500, "item", []),
        ],
    ),
    (
        "سوق الخضار الطازجة",
        "",
        "supermarket",
        33.3005,
        44.4175,
        True,
        [
            ("خضار", "طماطة", "تەماتە", "Tomatoes", 1500, "kg", []),
            ("خضار", "خيار", "خەیار", "Cucumbers", 1250, "kg", []),
            ("فواكه", "تمر برحي", "خورمای بەرحی", "Barhi dates", 5000, "kg", []),
        ],
    ),
    (
        "مقهى أبو نواس",
        "drinks",
        "restaurant",
        33.3090,
        44.4150,
        False,
        [("مشروبات", "قهوة عربية", "قاوەی عەرەبی", "Arabic coffee", 2500, "item", [])],
    ),
]


class Command(BaseCommand):
    help = "Create demo stores, menus, an offer and a demo captain near Karrada, Baghdad."

    @transaction.atomic
    def handle(self, *args, **options):
        owner, _ = User.objects.get_or_create(
            phone=OWNER_PHONE, defaults={"role": User.Role.VENDOR, "name": "Demo store owner"}
        )
        User.objects.get_or_create(phone=CAPTAIN_PHONE, defaults={"role": User.Role.CAPTAIN, "name": "Demo captain"})

        old = Vendor.objects.filter(owner=owner)
        old_ids = list(old.values_list("pk", flat=True))
        # Keep stores that already have orders (they're protected); refresh the rest.
        old.filter(orders__isnull=True).delete()

        for name, cuisine, kind, lat, lng, is_open, products in STORES:
            vendor, _ = Vendor.objects.update_or_create(
                owner=owner,
                name=name,
                defaults={
                    "cuisine": cuisine,
                    "type": kind,
                    "location": Point(lng, lat, srid=4326),
                    "is_open": is_open,
                    "delivery_radius_km": Decimal("8"),
                    "status": Vendor.Status.APPROVED,
                },
            )
            if vendor.pk in old_ids:
                continue  # existing store with orders: keep its menu
            for section, ar, ku, en, price, unit, modifiers in products:
                product = Product.objects.create(
                    vendor=vendor, menu_section=section, name_ar=ar, name_ku=ku, name_en=en, price=price, unit_type=unit
                )
                for group, m_ar, m_ku, m_en, delta, required in modifiers:
                    ProductModifier.objects.create(
                        product=product,
                        group_name=group,
                        name_ar=m_ar,
                        name_ku=m_ku,
                        name_en=m_en,
                        price_delta=delta,
                        is_required=required,
                    )

        now = timezone.now()
        Offer.objects.update_or_create(
            title="خصم 10% على أول طلب",
            defaults={
                "vendor": None,
                "type": Offer.Type.PERCENT,
                "value": 10,
                "min_order": 10000,
                "starts_at": now - timedelta(days=1),
                "ends_at": now + timedelta(days=30),
                "is_banner": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Demo data ready: {len(STORES)} stores near Karrada, Baghdad."))
        self.stdout.write(f"Store owner: {OWNER_PHONE}  Captain: {CAPTAIN_PHONE}")
