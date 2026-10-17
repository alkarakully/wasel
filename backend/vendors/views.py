from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import F, Prefetch
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

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
                Prefetch("products", queryset=Product.objects.prefetch_related("modifiers"))
            )
        return queryset


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    """Offers running right now. `?banner=1` returns only home-banner offers."""

    serializer_class = OfferSerializer

    def get_queryset(self):
        now = timezone.now()
        queryset = Offer.objects.filter(starts_at__lte=now, ends_at__gte=now)
        if self.request.query_params.get("banner") == "1":
            queryset = queryset.filter(is_banner=True)
        return queryset
