from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import F, Prefetch
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import access
from .models import Offer, Product, Vendor
from .serializers import OfferSerializer, VendorDetailSerializer, VendorSerializer


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Restaurants and supermarkets.

    `?lat=..&lng=..` limits the list to vendors that deliver to that spot,
    nearest first. `?type=` and `?cuisine=` filter further. Open vendors
    always come before closed ones.
    """

    def get_serializer_class(self):
        return VendorDetailSerializer if self.action == "retrieve" else VendorSerializer

    def get_queryset(self):
        queryset = Vendor.objects.all()
        params = self.request.query_params

        if vendor_type := params.get("type"):
            queryset = queryset.filter(type=vendor_type)
        if cuisine := params.get("cuisine"):
            queryset = queryset.filter(cuisine=cuisine)

        lat, lng = params.get("lat"), params.get("lng")
        if lat and lng:
            try:
                point = Point(float(lng), float(lat), srid=4326)
            except ValueError:
                raise ValidationError("lat and lng must be numbers")
            queryset = (
                queryset.annotate(distance=Distance("location", point))
                .filter(distance__lte=F("delivery_radius_km") * 1000)
                .order_by("-is_open", "distance")
            )
        else:
            queryset = queryset.order_by("-is_open", "name")

        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                Prefetch("products", queryset=Product.objects.filter(is_archived=False).prefetch_related("modifiers"))
            )
        return queryset

    # --- Store owner -----------------------------------------------------------

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        """
        Stores the signed-in user owns or works at, with full menus and their
        role there ("owner", "manager" or "cashier"), which decides what they see.
        """
        stores = (
            access.stores_for(request.user)
            .order_by("name")
            .prefetch_related(
                Prefetch("products", queryset=Product.objects.filter(is_archived=False).prefetch_related("modifiers"))
            )
        )
        data = VendorDetailSerializer(stores, many=True).data
        for store, row in zip(stores, data):
            row["my_role"] = access.role_for(store, request.user)
        return Response(data)

    @action(detail=True, methods=["post"], url_path="open", permission_classes=[permissions.IsAuthenticated])
    def set_open(self, request, pk=None):
        """POST {is_open} opens or closes the store for new orders."""
        store = self.get_object()
        if not access.can(store, request.user, "orders"):
            return Response({"error": "not_allowed", "detail": "Only the store's team can do this."}, status=403)
        store.is_open = serializers.BooleanField().to_internal_value(request.data.get("is_open"))
        store.save(update_fields=["is_open"])
        return Response({"id": store.pk, "is_open": store.is_open})


class ProductAvailabilityView(APIView):
    """POST /api/products/{id}/availability/ {is_available}: mark an item in or out of stock."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        product = Product.objects.select_related("vendor").filter(pk=pk).first()
        if product is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not access.can(product.vendor, request.user, "orders"):
            return Response({"error": "not_allowed", "detail": "Only the store's team can do this."}, status=403)
        product.is_available = serializers.BooleanField().to_internal_value(request.data.get("is_available"))
        product.save(update_fields=["is_available"])
        return Response({"id": product.pk, "is_available": product.is_available})


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    """Offers running right now. `?banner=1` returns only home-banner offers."""

    serializer_class = OfferSerializer

    def get_queryset(self):
        now = timezone.now()
        queryset = Offer.objects.filter(starts_at__lte=now, ends_at__gte=now)
        if self.request.query_params.get("banner") == "1":
            queryset = queryset.filter(is_banner=True)
        return queryset
