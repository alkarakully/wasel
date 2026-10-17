from django.contrib.gis.geos import Point
from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order
from .pricing import PricingError, build_quote
from .serializers import CartSerializer, OrderSerializer, PlaceOrderSerializer, quote_to_dict
from .services import place_order


def pricing_error_response(error):
    return Response({"error": error.code, "detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    Orders the signed-in user is part of: as the customer, the captain,
    or the owner of the vendor.

    POST /api/orders/quote/ prices a cart without placing it.
    POST /api/orders/ places the order at exactly the quoted price.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Order.objects.filter(Q(customer=user) | Q(captain=user) | Q(vendor__owner=user))
            .distinct()
            .prefetch_related("items__modifiers")
        )

    @action(detail=False, methods=["post"])
    def quote(self, request):
        cart = CartSerializer(data=request.data)
        cart.is_valid(raise_exception=True)
        data = cart.validated_data
        try:
            quote = build_quote(
                request.user,
                data["vendor"],
                data["items"],
                Point(data["delivery_longitude"], data["delivery_latitude"], srid=4326),
                offer_id=data.get("offer"),
                tip=data["tip"],
            )
        except PricingError as error:
            return pricing_error_response(error)
        return Response(quote_to_dict(quote))

    def create(self, request, *args, **kwargs):
        cart = PlaceOrderSerializer(data=request.data)
        cart.is_valid(raise_exception=True)
        data = cart.validated_data
        try:
            order = place_order(
                request.user,
                vendor=data["vendor"],
                items=data["items"],
                latitude=data["delivery_latitude"],
                longitude=data["delivery_longitude"],
                delivery_address=data["delivery_address"],
                payment_type=data["payment_type"],
                offer=data.get("offer"),
                tip=data["tip"],
            )
        except PricingError as error:
            return pricing_error_response(error)
        order = self.get_queryset().get(pk=order.pk)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)
