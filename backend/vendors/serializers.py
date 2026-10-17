from rest_framework import serializers

from orders.pricing import delivery_fee_for

from .models import Offer, Product, ProductModifier, Vendor


class ProductModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductModifier
        fields = ["id", "group_name", "name_ar", "name_ku", "name_en", "price_delta", "is_required"]


class ProductSerializer(serializers.ModelSerializer):
    modifiers = ProductModifierSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name_ar",
            "name_ku",
            "name_en",
            "menu_section",
            "price",
            "unit_type",
            "is_available",
            "modifiers",
        ]


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
        return str(delivery_fee_for(distance.m)) if distance is not None else None

    def get_latitude(self, vendor):
        return vendor.location.y

    def get_longitude(self, vendor):
        return vendor.location.x


class VendorDetailSerializer(VendorSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta(VendorSerializer.Meta):
        fields = VendorSerializer.Meta.fields + ["products"]


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ["id", "vendor", "title", "type", "value", "min_order", "starts_at", "ends_at", "is_banner"]
