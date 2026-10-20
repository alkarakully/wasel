from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from rest_framework.routers import DefaultRouter

from orders.views import CaptainLocationView, CaptainStatusView, CurrentOfferView, OfferAnswerView, OrderViewSet
from billing.api import BillingView, CloseWeeksView, MarkPaidView, StatementView
from billing.api import PayoutsView as BillingPayouts
from vendors.manage import HoursView, InviteView, MemberView, ProductsView, ProductView, TeamView
from vendors.onboarding import AnswerInviteView, ApplicationsView, MyInvitesView
from regions.views import CountriesView
from vendors.reports import ReportView
from vendors.views import OfferViewSet, ProductAvailabilityView, VendorViewSet

admin.site.site_header = "Wasel admin"
admin.site.site_title = "Wasel admin"
admin.site.index_title = "Platform administration"
# Day-to-day work happens in the platform admin; only superusers get into this one.
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("offers", OfferViewSet, basename="offer")
router.register("orders", OrderViewSet, basename="order")

def healthz(request):
    """For Docker and load balancers: the app is up and can reach the database."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path(settings.DJANGO_ADMIN_PATH, admin.site.urls),
    path("api/console/", include("console.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/countries/", CountriesView.as_view(), name="countries"),
    path("api/captain/location/", CaptainLocationView.as_view(), name="captain-location"),
    path("api/captain/status/", CaptainStatusView.as_view(), name="captain-status"),
    path("api/dispatch/offers/current/", CurrentOfferView.as_view(), name="dispatch-current"),
    path("api/dispatch/offers/<int:pk>/accept/", OfferAnswerView.as_view(answer="accept"), name="dispatch-accept"),
    path("api/dispatch/offers/<int:pk>/decline/", OfferAnswerView.as_view(answer="decline"), name="dispatch-decline"),
    path("api/products/<int:pk>/availability/", ProductAvailabilityView.as_view(), name="product-availability"),
    path("api/ops/payouts/", BillingPayouts.as_view(), name="ops-payouts"),
    path("api/ops/payouts/close/", CloseWeeksView.as_view(), name="ops-payouts-close"),
    path("api/ops/payouts/<int:pk>/paid/", MarkPaidView.as_view(), name="ops-payout-paid"),
    path("api/ops/", include("ops.urls")),
    # Store self-service (team, menu, hours, reports, billing).
    path("api/vendors/<int:pk>/team/", TeamView.as_view(), name="store-team"),
    path("api/vendors/<int:pk>/team/<int:member_id>/", MemberView.as_view(), name="store-member"),
    path("api/vendors/<int:pk>/team/invites/<int:invite_id>/", InviteView.as_view(), name="store-invite"),
    path("api/vendors/<int:pk>/products/", ProductsView.as_view(), name="store-products"),
    path("api/vendors/<int:pk>/hours/", HoursView.as_view(), name="store-hours"),
    path("api/vendors/<int:pk>/report/", ReportView.as_view(), name="store-report"),
    path("api/vendors/<int:pk>/billing/", BillingView.as_view(), name="store-billing"),
    path("api/vendors/<int:pk>/statements/<int:statement_id>/", StatementView.as_view(), name="store-statement"),
    path("api/products/<int:pk>/", ProductView.as_view(), name="product"),
    # Onboarding: applying to sell on Wasel and answering team invites.
    path("api/store-applications/", ApplicationsView.as_view(), name="store-applications"),
    path("api/store-invites/", MyInvitesView.as_view(), name="my-invites"),
    path("api/store-invites/<int:pk>/accept/", AnswerInviteView.as_view(answer="accept"), name="invite-accept"),
    path("api/store-invites/<int:pk>/decline/", AnswerInviteView.as_view(answer="decline"), name="invite-decline"),
    path("api/", include(router.urls)),
    # Staff operations page; signs in through the admin.
    # The old operations page; the platform admin (/admin/) does all of it now.
    path("ops/", RedirectView.as_view(url="/admin/", permanent=False), name="ops"),
    path("login/", TemplateView.as_view(template_name="accounts/login.html"), name="login"),
    path("track/<int:order_id>/", TemplateView.as_view(template_name="orders/track.html", extra_context={"map_styles": settings.MAP_STYLES}), name="track-order"),
    path("api-auth/", include("rest_framework.urls")),
]
