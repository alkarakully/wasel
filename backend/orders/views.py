from django.contrib.gis.geos import Point
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from . import dispatch, realtime, workflow
from .models import CaptainLocation, DispatchOffer, Order
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


class OrderPagination(PageNumberPagination):
    # A busy store board asks for all open orders at once (?page_size=100).
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def pricing_error_response(error):
    return Response({"error": error.code, "detail": error.detail}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    Orders the signed-in user is part of: as the customer, the captain,
    or someone who works at the store (owner, manager or cashier).

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
    pagination_class = OrderPagination

    def get_queryset(self):
        user = self.request.user
        orders = Order.objects.all()
        # ?status=received,preparing narrows the list (the store board uses it).
        if statuses := self.request.query_params.get("status"):
            orders = orders.filter(status__in=statuses.split(","))
        return (
            orders.filter(
                Q(customer=user) | Q(captain=user) | Q(vendor__owner=user) | Q(vendor__members__user=user)
            )
            .distinct()
            .select_related("vendor", "customer", "captain__location")
            .prefetch_related("items__product", "items__modifiers__modifier")
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

    def _step(self, request, pk, run, input_serializer=None, then=None):
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
        # Runs before the broadcast so captains see the order's final state
        # (e.g. offered to one captain rather than open to all).
        if then is not None:
            then(order)
        realtime.broadcast_order(order.pk, was_available)
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        # Offer it to the nearest free captain; the broadcast announces it to
        # everyone if nobody is available.
        return self._step(
            request, pk, workflow.accept, AcceptSerializer, then=lambda o: dispatch.offer_next(o.pk, announce_if_none=False)
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._step(request, pk, workflow.reject, RejectSerializer, then=lambda o: dispatch.withdraw(o.pk, "cancelled"))

    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):
        return self._step(request, pk, workflow.mark_ready)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._step(request, pk, workflow.cancel, ReasonSerializer, then=lambda o: dispatch.withdraw(o.pk, "cancelled"))

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
        offered = DispatchOffer.objects.filter(
            order=OuterRef("pk"), status=DispatchOffer.Status.PENDING, expires_at__gt=timezone.now()
        )
        orders = (
            Order.objects.filter(status__in=[Order.Status.PREPARING, Order.Status.READY], captain__isnull=True)
            # Orders being offered to one captain stay hidden until the offer ends.
            .exclude(Exists(offered))
            .order_by("created_at")
            .select_related("vendor", "customer", "captain__location")
            .prefetch_related("items__product", "items__modifiers__modifier")
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


def _captains_only(request):
    if request.user.role != User.Role.CAPTAIN:
        return Response({"error": "not_allowed", "detail": "Only captains can do this."}, status=status.HTTP_403_FORBIDDEN)
    return None


class CaptainStatusView(APIView):
    """
    POST /api/captain/status/ {online}: start or stop taking orders.
    Going offline turns down any offer the captain hasn't answered.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if denied := _captains_only(request):
            return denied
        online = serializers.BooleanField().to_internal_value(request.data.get("online"))
        CaptainLocation.objects.update_or_create(
            captain=request.user, defaults={"is_online": online}, create_defaults={"is_online": online, "updated_at": timezone.now()}
        )
        if not online:
            for offer_id in DispatchOffer.objects.filter(
                captain=request.user, status=DispatchOffer.Status.PENDING
            ).values_list("pk", flat=True):
                try:
                    dispatch.decline(offer_id, request.user)
                except dispatch.OfferGone:
                    pass
        return Response({"online": online})


def _offer_data(offer):
    return {
        "id": offer.pk,
        "order": OrderSerializer(offer.order).data,
        "distance_km": round(offer.distance_m / 1000, 2),
        "expires_at": offer.expires_at.isoformat(),
    }


class CurrentOfferView(APIView):
    """GET /api/dispatch/offers/current/: the captain's open offer, if any (204 otherwise)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if denied := _captains_only(request):
            return denied
        offer = (
            DispatchOffer.objects.filter(
                captain=request.user, status=DispatchOffer.Status.PENDING, expires_at__gt=timezone.now()
            )
            .select_related("order__vendor")
            .first()
        )
        if offer is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(_offer_data(offer))


class OfferAnswerView(APIView):
    """POST /api/dispatch/offers/{id}/accept/ or .../decline/."""

    permission_classes = [permissions.IsAuthenticated]
    answer = None  # "accept" or "decline"

    def post(self, request, pk):
        if denied := _captains_only(request):
            return denied
        try:
            if self.answer == "accept":
                order = dispatch.accept(pk, request.user)
            else:
                dispatch.decline(pk, request.user)
        except dispatch.OfferGone as error:
            return Response({"error": "offer_gone", "detail": str(error)}, status=status.HTTP_409_CONFLICT)
        except workflow.WorkflowError as error:
            return Response({"error": error.code, "detail": error.detail}, status=error.status)
        if self.answer == "decline":
            return Response(status=status.HTTP_204_NO_CONTENT)
        realtime.broadcast_order(order.pk, was_available=False)
        order = Order.objects.select_related("vendor", "customer").get(pk=order.pk)
        return Response(OrderSerializer(order, context={"request": request}).data)
