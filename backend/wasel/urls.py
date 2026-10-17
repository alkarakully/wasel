from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from orders.views import OrderViewSet
from vendors.views import OfferViewSet, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("offers", OfferViewSet, basename="offer")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
