from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from orders.views import CaptainLocationView, OrderViewSet
from vendors.views import OfferViewSet, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("offers", OfferViewSet, basename="offer")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/captain/location/", CaptainLocationView.as_view(), name="captain-location"),
    path("api/", include(router.urls)),
    path("login/", TemplateView.as_view(template_name="accounts/login.html"), name="login"),
    path("track/<int:order_id>/", TemplateView.as_view(template_name="orders/track.html", extra_context={"map_styles": settings.MAP_STYLES}), name="track-order"),
    path("api-auth/", include("rest_framework.urls")),
]
