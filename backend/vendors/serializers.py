from django.utils import timezone
from rest_framework import serializers

from orders.pricing import delivery_fee_for
from regions.regions import as_api
from regions.serializers import MoneyMixin

from .models import Offer, Product, ProductModifier, Vendor
from .search import matching_products


class ProductModifierSerializer(MoneyMixin, serializers.ModelSerializer):
    money_fields = ("price_delta",)

    class Meta:
        model = ProductModifier
        fields = ["id", "group_name", "name_ar", "name_ku", "name_en", "price_delta", "is_required"]

    def currency_for(self, modifier):
        return modifier.product.vendor.currency


class ProductSerializer(MoneyMixin, serializers.ModelSerializer):
    money_fields = ("price",)
    modifiers = ProductModifierSerializer(many=True, read_only=True)
    # Path on the API's own host ("/media/products/12-ab.jpg"), or null.
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name_ar",
            "name_ku",
            "name_en",
            "description_ar",
            "description_ku",
            "description_en",
            "menu_section",
            "image",
            "price",
            "unit_type",
            "is_available",
            "modifiers",
        ]

    def currency_for(self, product):
        return product.vendor.currency

    def get_image(self, product):
        return product.image.url if product.image else None


class VendorSerializer(serializers.ModelSerializer):
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    # Only filled when the list is asked for a delivery spot (?lat=&lng=).
    distance_km = serializers.SerializerMethodField()
    delivery_fee = serializers.SerializerMethodField()
    # The store's headline offer running now, for a badge on its card (list only).
    offer = serializers.SerializerMethodField()
    # In a search (?q=), up to three dishes that matched (list only).
    matches = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "type",
            "cuisine",
            "country",
            "currency",
            "latitude",
            "longitude",
            "delivery_radius_km",
            "is_open",
            "opening_hours",
            "distance_km",
            "delivery_fee",
            "offer",
            "matches",
        ]

    def get_distance_km(self, vendor):
        distance = getattr(vendor, "distance", None)
        return round(distance.km, 2) if distance is not None else None

    def get_delivery_fee(self, vendor):
        # Standard fee before Wasel Plus or offers; checkout shows the final price.
        distance = getattr(vendor, "distance", None)
        if distance is None:
            return None
        return as_api(delivery_fee_for(distance.m, vendor.country), vendor.currency)

    def get_offer(self, vendor):
        offers = getattr(vendor, "running_offers", None)
        if not offers:
            return None
        # Percent first (the biggest), then buy-one-get-one, amount off, free delivery.
        rank = {Offer.Type.PERCENT: 0, Offer.Type.BOGO: 1, Offer.Type.FIXED: 2, Offer.Type.FREE_DELIVERY: 3}
        best = min(offers, key=lambda o: (rank.get(o.type, 3), -o.value))
        return OfferSerializer(best).data

    def get_matches(self, vendor):
        menu = getattr(vendor, "menu", None)
        query = self.context["request"].query_params.get("q", "") if "request" in self.context else ""
        if menu is None or not query:
            return []
        return [
            {"id": p.id, "name_ar": p.name_ar, "name_ku": p.name_ku, "name_en": p.name_en}
            for p in matching_products(menu, query)
        ]

    def get_latitude(self, vendor):
        return vendor.location.y

    def get_longitude(self, vendor):
        return vendor.location.x


class VendorDetailSerializer(VendorSerializer):
    products = ProductSerializer(many=True, read_only=True)
    # The store's own offers running now; checkout applies the best one.
    offers = serializers.SerializerMethodField()

    class Meta(VendorSerializer.Meta):
        # A store page lists every offer and the menu, so the card-only fields stay out.
        fields = [f for f in VendorSerializer.Meta.fields if f not in ("offer", "matches")] + ["products", "offers"]

    def get_offers(self, vendor):
        now = timezone.now()
        running = vendor.offers.filter(starts_at__lte=now, ends_at__gte=now).select_related("product").order_by("ends_at")
        return OfferSerializer(running, many=True).data


class OfferSerializer(MoneyMixin, serializers.ModelSerializer):
    money_fields = ("min_order",)
    # Buy one, get one free: the item it's on.
    product = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id", "vendor", "country", "currency", "title", "type", "value", "min_order", "starts_at", "ends_at",
            "is_banner", "product",
        ]

    def get_product(self, offer):
        p = offer.product
        return {"id": p.pk, "name_ar": p.name_ar, "name_ku": p.name_ku, "name_en": p.name_en} if p else None

    def to_representation(self, offer):
        data = super().to_representation(offer)
        # A fixed offer's value is money; a percent stays a plain number.
        if offer.type == Offer.Type.FIXED:
            data["value"] = as_api(offer.value, offer.currency)
        else:
            data["value"] = f"{offer.value.normalize():f}"
        return data
