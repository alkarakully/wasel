from django.contrib.gis.geos import Point
from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from . import realtime, workflow
from .models import Order
from .pricing import PricingError, build_quote
from .serializers import (
    AcceptSerializer,
    CartSerializer,
    DeliverSerializer,
    LocationSerializer,
    OrderSerializer,
    PlaceOrderSerializer,
    ReasonSerializer,
    RejectSerializer,
    quote_to_dict,
)
from .services import place_order
from .tracking import update_captain_location


def pricing_error_response(error):
    return Response({"error": error.code, "detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    Orders the signed-in user is part of: as the customer, the captain,
    or the owner of the vendor.

    POST /api/orders/quote/ prices a cart without placing it.
    POST /api/orders/ places the order at exactly the quoted price.

    Status steps, each POST /api/orders/{id}/<step>/:
      store:    accept {prep_minutes}, reject {reason}, ready
      customer: cancel {reason?}  (only before the store accepts)
      captain:  claim, pickup, deliver {pin}
    GET /api/orders/available/ lists orders waiting for a captain.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        user = self.request.user
        return (
            Order.objects.filter(Q(customer=user) | Q(captain=user) | Q(vendor__owner=user))
            .distinct()
            .select_related("vendor", "customer", "captain__location")
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
        realtime.broadcast_order(order.pk)
        order = self.get_queryset().get(pk=order.pk)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    # --- Status steps ------------------------------------------------------------

    def _step(self, request, pk, run, input_serializer=None):
        # get_object() limits steps to orders the user is part of (404 otherwise).
        order = self.get_object()
        data = {}
        if input_serializer is not None:
            serializer = input_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
        was_available = realtime.was_available(order)
        try:
            order = run(order.pk, request.user, **data)
        except workflow.WorkflowError as error:
            return Response({"error": error.code, "detail": error.detail}, status=error.status)
        realtime.broadcast_order(order.pk, was_available)
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._step(request, pk, workflow.accept, AcceptSerializer)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._step(request, pk, workflow.reject, RejectSerializer)

    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):
        return self._step(request, pk, workflow.mark_ready)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._step(request, pk, workflow.cancel, ReasonSerializer)

    @action(detail=True, methods=["post"])
    def pickup(self, request, pk=None):
        return self._step(request, pk, workflow.pickup)

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        return self._step(request, pk, workflow.deliver, DeliverSerializer)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        # The captain isn't on the order yet, so it isn't in get_queryset().
        try:
            order = workflow.claim(pk, request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except workflow.WorkflowError as error:
            return Response({"error": error.code, "detail": error.detail}, status=error.status)
        # Before the claim it was waiting for a captain; now it isn't.
        realtime.broadcast_order(order.pk, was_available=True)
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)

    @action(detail=False, methods=["get"])
    def available(self, request):
        """Orders a captain can take: accepted by the store and not yet claimed, oldest first."""
        if request.user.role != User.Role.CAPTAIN:
            return Response(
                {"error": "not_allowed", "detail": "Only captains can see available orders."},
                status=status.HTTP_403_FORBIDDEN,
            )
        orders = (
            Order.objects.filter(status__in=[Order.Status.PREPARING, Order.Status.READY], captain__isnull=True)
            .order_by("created_at")
            .select_related("vendor", "customer", "captain__location")
            .prefetch_related("items__modifiers")
        )
        page = self.paginate_queryset(orders)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class CaptainLocationView(APIView):
    """
    POST /api/captain/location/ {lat, lng, heading?, speed?}

    For when the captain app is in the background and its socket is closed.
    Updates closer than 2 seconds apart are ignored (still 204).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != User.Role.CAPTAIN:
            return Response(
                {"error": "not_allowed", "detail": "Only captains send locations."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = LocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_captain_location(request.user, **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)
