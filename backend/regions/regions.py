"""
The countries Wasel runs stores in, each with its own currency, clock and prices.

A store belongs to one of these; its orders, fees, statements and reports use
that country's currency, time zone and first day of the week. Prices here can
be tuned per deployment with settings.REGIONS = {"SA": {"SERVICE_FEE": "2"}}.
"""

from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo

from django.conf import settings

DEFAULT = "IQ"

# date.weekday(): Monday 0 ... Sunday 6
MONDAY, SATURDAY, SUNDAY = 0, 5, 6


@dataclass(frozen=True)
class Region:
    country: str
    currency: str
    decimals: int
    time_zone: str
    week_starts: int
    center: tuple  # (lat, lng)
    # Rough box (south, west, north, east) for "is this map spot in the country?".
    bounds: tuple
    pricing: dict = field(default_factory=dict)
    max_wallet_adjustment: Decimal = Decimal(0)
    # Quick tip choices shown at checkout.
    tips: tuple = ()

    @property
    def tz(self):
        return ZoneInfo(self.time_zone)

    @property
    def step(self):
        """The smallest amount: 1 for IQD, 0.01 for SAR, 0.001 for KWD."""
        return Decimal(1).scaleb(-self.decimals)

    def contains(self, lat, lng):
        south, west, north, east = self.bounds
        return south <= lat <= north and west <= lng <= east


def _p(**values):
    return {key: Decimal(str(value)) for key, value in values.items()}


_REGIONS = {
    "IQ": Region(
        "IQ", "IQD", 0, "Asia/Baghdad", SATURDAY, (33.3152, 44.3661), (29.0, 38.7, 37.4, 48.7),
        _p(DELIVERY_BASE_FEE=1500, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=250, FEE_ROUNDING=250, SERVICE_FEE=500,
           PLUS_FREE_DELIVERY_MIN=15000, PLUS_SERVICE_FEE=250, MAX_TIP=50000),
        Decimal(1_000_000), (500, 1000, 2000),
    ),
    "SA": Region(
        "SA", "SAR", 2, "Asia/Riyadh", SUNDAY, (24.7136, 46.6753), (16.3, 34.5, 32.2, 55.7),
        _p(DELIVERY_BASE_FEE=7, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=1.5, FEE_ROUNDING=0.5, SERVICE_FEE=2,
           PLUS_FREE_DELIVERY_MIN=50, PLUS_SERVICE_FEE=1, MAX_TIP=200),
        Decimal(3000), (2, 5, 10),
    ),
    "AE": Region(
        "AE", "AED", 2, "Asia/Dubai", MONDAY, (25.2048, 55.2708), (22.6, 51.5, 26.1, 56.4),
        _p(DELIVERY_BASE_FEE=7, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=1.5, FEE_ROUNDING=0.5, SERVICE_FEE=2,
           PLUS_FREE_DELIVERY_MIN=50, PLUS_SERVICE_FEE=1, MAX_TIP=200),
        Decimal(3000), (2, 5, 10),
    ),
    "KW": Region(
        "KW", "KWD", 3, "Asia/Kuwait", SUNDAY, (29.3759, 47.9774), (28.5, 46.5, 30.1, 48.5),
        _p(DELIVERY_BASE_FEE=0.5, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=0.1, FEE_ROUNDING=0.05, SERVICE_FEE=0.15,
           PLUS_FREE_DELIVERY_MIN=5, PLUS_SERVICE_FEE=0.075, MAX_TIP=20),
        Decimal(300), (Decimal("0.25"), Decimal("0.5"), 1),
    ),
    "QA": Region(
        "QA", "QAR", 2, "Asia/Qatar", SUNDAY, (25.2854, 51.5310), (24.4, 50.7, 26.2, 51.7),
        _p(DELIVERY_BASE_FEE=7, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=1.5, FEE_ROUNDING=0.5, SERVICE_FEE=2,
           PLUS_FREE_DELIVERY_MIN=50, PLUS_SERVICE_FEE=1, MAX_TIP=200),
        Decimal(3000), (2, 5, 10),
    ),
    "BH": Region(
        "BH", "BHD", 3, "Asia/Bahrain", SUNDAY, (26.2285, 50.5860), (25.5, 50.3, 26.4, 50.9),
        _p(DELIVERY_BASE_FEE=0.7, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=0.15, FEE_ROUNDING=0.05, SERVICE_FEE=0.2,
           PLUS_FREE_DELIVERY_MIN=5, PLUS_SERVICE_FEE=0.1, MAX_TIP=20),
        Decimal(300), (Decimal("0.25"), Decimal("0.5"), 1),
    ),
    "OM": Region(
        "OM", "OMR", 3, "Asia/Muscat", SUNDAY, (23.5880, 58.3829), (16.6, 51.9, 26.4, 59.9),
        _p(DELIVERY_BASE_FEE=0.7, DELIVERY_BASE_KM=2, DELIVERY_FEE_PER_KM=0.15, FEE_ROUNDING=0.05, SERVICE_FEE=0.2,
           PLUS_FREE_DELIVERY_MIN=5, PLUS_SERVICE_FEE=0.1, MAX_TIP=20),
        Decimal(300), (Decimal("0.25"), Decimal("0.5"), 1),
    ),
}

CODES = list(_REGIONS)
CURRENCIES = {region.currency: region for region in _REGIONS.values()}
CHOICES = [(code, code) for code in CODES]
CURRENCY_CHOICES = [(region.currency, region.currency) for region in _REGIONS.values()]


@lru_cache(maxsize=None)
def _region(country, overrides_key):
    base = _REGIONS[country]
    overrides = getattr(settings, "REGIONS", {}).get(country, {})
    if not overrides:
        return base
    return replace(base, pricing={**base.pricing, **{k: Decimal(str(v)) for k, v in overrides.items()}})


def region(country=None):
    """The region for a country code (Iraq when missing or unknown)."""
    country = country if country in _REGIONS else DEFAULT
    return _region(country, repr(getattr(settings, "REGIONS", {}).get(country)))


def for_currency(currency):
    return CURRENCIES.get(currency) or _REGIONS[DEFAULT]


def _area(r):
    south, west, north, east = r.bounds
    return (north - south) * (east - west)


# Boxes overlap near borders, so the smallest country that fits wins (Kuwait City
# is inside Iraq's box too). Good enough for a default; stores can say otherwise.
_BY_SIZE = sorted(_REGIONS, key=lambda code: _area(_REGIONS[code]))


def where(lat, lng):
    """The operating country this map spot is most likely in, or None."""
    for code in _BY_SIZE:
        if _REGIONS[code].contains(lat, lng):
            return code
    return None


def quantize(amount, currency):
    """Round to the currency's smallest unit, halves up."""
    return Decimal(amount).quantize(for_currency(currency).step, rounding=ROUND_HALF_UP)


def as_api(amount, currency):
    """Money for JSON: a string with exactly the currency's decimals ("18000", "12.50", "0.750")."""
    return str(quantize(amount or 0, currency))
