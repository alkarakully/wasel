from rest_framework import serializers

from .models import Order, OrderItem, OrderItemModifier


class OrderItemModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemModifier
        fields = ["modifier", "price_delta"]


class OrderItemSerializer(serializers.ModelSerializer):
    modifiers = OrderItemModifierSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "unit_price", "line_total", "modifiers"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "vendor",
            "captain",
            "status",
            "payment_type",
            "delivery_address",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "discount",
            "tip",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        ]
