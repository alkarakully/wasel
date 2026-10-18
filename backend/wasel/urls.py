from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from orders.views import CaptainLocationView, CaptainStatusView, CurrentOfferView, OfferAnswerView, OrderViewSet
from notifications.views import DeviceView
from vendors.views import OfferViewSet, ProductAvailabilityView, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("offers", OfferViewSet, basename="offer")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/devices/", DeviceView.as_view(), name="devices"),
    path("api/captain/location/", CaptainLocationView.as_view(), name="captain-location"),
    path("api/captain/status/", CaptainStatusView.as_view(), name="captain-status"),
    path("api/dispatch/offers/current/", CurrentOfferView.as_view(), name="dispatch-current"),
    path("api/dispatch/offers/<int:pk>/accept/", OfferAnswerView.as_view(answer="accept"), name="dispatch-accept"),
    path("api/dispatch/offers/<int:pk>/decline/", OfferAnswerView.as_view(answer="decline"), name="dispatch-decline"),
    path("api/products/<int:pk>/availability/", ProductAvailabilityView.as_view(), name="product-availability"),
    path("api/", include(router.urls)),
    path("login/", TemplateView.as_view(template_name="accounts/login.html"), name="login"),
    path("track/<int:order_id>/", TemplateView.as_view(template_name="orders/track.html", extra_context={"map_styles": settings.MAP_STYLES}), name="track-order"),
    path("api-auth/", include("rest_framework.urls")),
]
