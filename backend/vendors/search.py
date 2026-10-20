"""
Store search for the customer app: by store name, dish, description or menu section,
or by what kind of place it is ("صيدلية", "pizza", "حلويات").

Arabic is written many ways (أ/إ/ا, ى/ي, ة/ه, with or without harakat), and
Kurdish uses ک and ی where Arabic keyboards type ك and ي, so text and query
are both folded to one spelling before comparing.
"""

from django.db.models import BooleanField, Case, Exists, F, Func, OuterRef, Q, Value, When
from django.db.models.functions import Lower

from .models import Product, Vendor

# Each character in _FROM becomes the one at the same place in _TO; the rest of
# _FROM (harakat and tatweel) is dropped. Same rule as PostgreSQL translate().
_MAP_FROM, _MAP_TO = "أإآٱىيكةؤئ", "ااااییکهوی"
_DROP = "ًٌٍَُِّْـ"
_FROM = _MAP_FROM + _DROP
_TABLE = str.maketrans(_MAP_FROM, _MAP_TO, _DROP)

# Words people search for a kind of place, in Arabic, Kurdish and English.
KEYWORDS = {
    ("type", Vendor.Type.RESTAURANT): ["مطعم", "مطاعم", "خواردنگە", "restaurant", "food"],
    ("type", Vendor.Type.SUPERMARKET): ["سوبرماركت", "سوق", "بقالة", "مارکێت", "supermarket", "grocery"],
    ("type", Vendor.Type.CAFE): ["مقهى", "كافيه", "قهوة", "حلويات", "مخبز", "کافێ", "شیرینی", "cafe", "coffee", "bakery"],
    ("type", Vendor.Type.PHARMACY): ["صيدلية", "صيدليه", "دواء", "دەرمانخانە", "pharmacy", "medicine"],
    ("type", Vendor.Type.CONVENIENCE): ["ماركت", "محل", "منزلية", "دوکان", "convenience", "household", "mart"],
    ("type", Vendor.Type.FLOWERS): ["ورد", "زهور", "هدايا", "گوڵ", "دیاری", "flowers", "flower", "gifts"],
    ("cuisine", Vendor.Cuisine.EASTERN): ["شرقي", "رۆژهەڵاتی", "eastern"],
    ("cuisine", Vendor.Cuisine.WESTERN): ["غربي", "بيتزا", "پیتزا", "رۆژئاوایی", "western", "pizza"],
    ("cuisine", Vendor.Cuisine.FAST_FOOD): ["وجبات سريعة", "برغر", "بەرگر", "fast food", "burger"],
    ("cuisine", Vendor.Cuisine.SWEETS): ["حلويات", "شیرینی", "sweets", "dessert"],
    ("cuisine", Vendor.Cuisine.DRINKS): ["مشروبات", "عصير", "خواردنەوە", "drinks", "juice"],
}


def fold(text):
    """The spelling search compares: lower case, one form per Arabic letter, no harakat."""
    return " ".join(text.translate(_TABLE).lower().split())


def _folded(field):
    return Lower(Func(F(field), Value(_FROM), Value(_MAP_TO), function="translate"))


PRODUCT_FIELDS = ["name_ar", "name_ku", "name_en", "description_ar", "description_ku", "description_en", "menu_section"]


def terms_for(query):
    return [term for term in fold(query).split() if term]


def search(vendors, query):
    """`vendors` narrowed to those matching every word of `query`, with `name_match` set."""
    terms = terms_for(query)
    if not terms:
        return vendors.none()
    folded_query = " ".join(terms)
    kinds = [kind for kind, words in KEYWORDS.items() if any(fold(word) in folded_query for word in words)]

    vendors = vendors.annotate(folded_name=_folded("name"))
    products = Product.objects.filter(vendor=OuterRef("pk"), is_archived=False)
    for i, field in enumerate(PRODUCT_FIELDS):
        products = products.annotate(**{f"f{i}": _folded(field)})

    for term in terms:
        in_products = Q()
        for i in range(len(PRODUCT_FIELDS)):
            in_products |= Q(**{f"f{i}__contains": term})
        match = Q(folded_name__contains=term) | Exists(products.filter(in_products))
        # A word naming a kind of place ("pharmacy") also matches every place of that kind.
        for (field, value), words in KEYWORDS.items():
            if (field, value) in kinds and any(term in fold(word).split() for word in words):
                match |= Q(**{field: value})
        vendors = vendors.filter(match)

    # Stores whose own name has every word come first.
    in_name = Q()
    for term in terms:
        in_name &= Q(folded_name__contains=term)
    return vendors.annotate(
        name_match=Case(When(in_name, then=Value(True)), default=Value(False), output_field=BooleanField())
    )


def matching_products(products, query, limit=3):
    """Names of up to `limit` dishes whose name, description or section has every word of `query`."""
    terms = terms_for(query)
    found = []
    for product in products:
        text = fold(" ".join(getattr(product, field) for field in PRODUCT_FIELDS))
        if terms and all(term in text for term in terms):
            found.append(product)
            if len(found) == limit:
                break
    return found
