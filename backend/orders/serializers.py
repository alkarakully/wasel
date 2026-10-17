from rest_framework import serializers

from .models import Order, OrderItem, OrderItemModifier
from .pricing import round_dinars


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
    delivery_pin = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "vendor",
            "captain",
            "offer",
            "status",
            "payment_type",
            "payment_status",
            "delivery_address",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "discount",
            "tip",
            "total_amount",
            "delivery_pin",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_delivery_pin(self, order):
        # Only the customer sees the PIN; they read it to the captain at the door.
        request = self.context.get("request")
        if request and request.user.pk == order.customer_id:
            return order.delivery_pin
        return None


# --- Input ---------------------------------------------------------------------


class CartItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=8, decimal_places=3, default=1)
    modifiers = serializers.ListField(child=serializers.IntegerField(), default=list)


class CartSerializer(serializers.Serializer):
    vendor = serializers.IntegerField()
    items = CartItemSerializer(many=True, allow_empty=False)
    delivery_latitude = serializers.FloatField(min_value=-90, max_value=90)
    delivery_longitude = serializers.FloatField(min_value=-180, max_value=180)
    offer = serializers.IntegerField(required=False, allow_null=True)
    tip = serializers.IntegerField(min_value=0, default=0)


class PlaceOrderSerializer(CartSerializer):
    delivery_address = serializers.CharField(max_length=255)
    payment_type = serializers.ChoiceField(choices=Order.PaymentType.choices, default=Order.PaymentType.COD)


def _money(amount):
    # Same format as the order serializer: whole dinars as a string.
    return str(round_dinars(amount))


def quote_to_dict(quote):
    return {
        "vendor": quote.vendor.pk,
        "items": [
            {
                "product": line.product.pk,
                "quantity": f"{line.quantity.normalize():f}",
                "modifiers": [modifier.pk for modifier in line.modifiers],
                "unit_price": _money(line.unit_price),
                "line_total": _money(line.line_total),
            }
            for line in quote.lines
        ],
        "subtotal": _money(quote.subtotal),
        "delivery_fee": _money(quote.delivery_fee),
        "service_fee": _money(quote.service_fee),
        "discount": _money(quote.discount),
        "offer": quote.offer.pk if quote.offer else None,
        "tip": _money(quote.tip),
        "total_amount": _money(quote.total_amount),
        "wasel_plus": quote.wasel_plus,
        "distance_km": round(quote.distance_m / 1000, 2),
    }
