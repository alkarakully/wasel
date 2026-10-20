from django.utils import timezone
from rest_framework import serializers

from orders.pricing import delivery_fee_for
from regions.regions import as_api
from regions.serializers import MoneyMixin

from .models import Offer, Product, ProductModifier, Vendor


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

    def get_latitude(self, vendor):
        return vendor.location.y

    def get_longitude(self, vendor):
        return vendor.location.x


class VendorDetailSerializer(VendorSerializer):
    products = ProductSerializer(many=True, read_only=True)
    # The store's own offers running now; checkout applies the best one.
    offers = serializers.SerializerMethodField()

    class Meta(VendorSerializer.Meta):
        fields = VendorSerializer.Meta.fields + ["products", "offers"]

    def get_offers(self, vendor):
        now = timezone.now()
        running = vendor.offers.filter(starts_at__lte=now, ends_at__gte=now).order_by("ends_at")
        return OfferSerializer(running, many=True).data


class OfferSerializer(MoneyMixin, serializers.ModelSerializer):
    money_fields = ("min_order",)

    class Meta:
        model = Offer
        fields = [
            "id", "vendor", "country", "currency", "title", "type", "value", "min_order", "starts_at", "ends_at",
            "is_banner",
        ]

    def to_representation(self, offer):
        data = super().to_representation(offer)
        # A fixed offer's value is money; a percent stays a plain number.
        if offer.type == Offer.Type.FIXED:
            data["value"] = as_api(offer.value, offer.currency)
        else:
            data["value"] = f"{offer.value.normalize():f}"
        return data
