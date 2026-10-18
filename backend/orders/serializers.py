from rest_framework import serializers

from .models import TRACKED_STATUSES, CaptainLocation, Order, OrderItem, OrderItemModifier
from .pricing import round_dinars


def names(obj):
    return {"ar": obj.name_ar, "ku": obj.name_ku, "en": obj.name_en}


class OrderItemModifierSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source="modifier.group_name", read_only=True)

    class Meta:
        model = OrderItemModifier
        fields = ["modifier", "group_name", "name", "price_delta"]

    def get_name(self, item_modifier):
        return names(item_modifier.modifier)


class OrderItemSerializer(serializers.ModelSerializer):
    modifiers = OrderItemModifierSerializer(many=True, read_only=True)
    # Names travel with the order so stores and captains see what to prepare.
    name = serializers.SerializerMethodField()
    unit_type = serializers.CharField(source="product.unit_type", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "name", "unit_type", "quantity", "unit_price", "line_total", "modifiers"]

    def get_name(self, item):
        return names(item.product)


def point_payload(point):
    return {"lat": point.y, "lng": point.x} if point else None


def location_payload(location):
    return {
        **point_payload(location.point),
        "heading": location.heading,
        "speed": location.speed,
        "updated_at": location.updated_at.isoformat(),
    }


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery_pin = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_location = serializers.SerializerMethodField()
    delivery_location = serializers.SerializerMethodField()
    captain_location = serializers.SerializerMethodField()
    customer_contact = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "vendor_location",
            "captain",
            "captain_location",
            "offer",
            "status",
            "payment_type",
            "payment_status",
            "delivery_address",
            "delivery_location",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "discount",
            "tip",
            "total_amount",
            "delivery_pin",
            "customer_contact",
            "items",
            "created_at",
            "accepted_at",
            "estimated_ready_at",
            "ready_at",
            "picked_up_at",
            "delivered_at",
            "cancelled_at",
            "cancelled_by",
            "cancel_reason",
            "updated_at",
        ]

    def get_vendor_location(self, order):
        return point_payload(order.vendor.location)

    def get_delivery_location(self, order):
        return point_payload(order.delivery_location)

    def get_captain_location(self, order):
        # Shown only while the order is active, so the map can start from the
        # captain's last known spot before live updates arrive.
        if not order.captain_id or order.status not in TRACKED_STATUSES:
            return None
        try:
            location = order.captain.location
        except CaptainLocation.DoesNotExist:
            return None
        return location_payload(location) if location.point else None

    def get_customer_contact(self, order):
        # The captain and the store can call the customer until the order is
        # finished; nobody else sees the number.
        request = self.context.get("request")
        if not request or order.status in (Order.Status.DELIVERED, Order.Status.CANCELLED):
            return None
        if request.user.pk not in (order.captain_id, order.vendor.owner_id):
            return None
        return {"name": order.customer.name, "phone": order.customer.phone}

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


class AcceptSerializer(serializers.Serializer):
    prep_minutes = serializers.IntegerField(min_value=5, max_value=120)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class DeliverSerializer(serializers.Serializer):
    pin = serializers.RegexField(r"^\d{4}$", error_messages={"invalid": "The PIN is 4 digits."})


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    heading = serializers.FloatField(min_value=0, max_value=360, required=False, allow_null=True, default=None)
    speed = serializers.FloatField(min_value=0, max_value=100, required=False, allow_null=True, default=None)


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
