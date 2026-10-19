from django.urls import path

from . import api

urlpatterns = [
    path("overview/", api.OverviewView.as_view(), name="ops-overview"),
    path("orders/", api.OrdersView.as_view(), name="ops-orders"),
    path("alerts/", api.AlertsView.as_view(), name="ops-alerts"),
    path("alerts/<int:pk>/resolve/", api.ResolveAlertView.as_view(), name="ops-alert-resolve"),
    path("captains/", api.CaptainsView.as_view(), name="ops-captains"),
    path("stores/", api.StoresView.as_view(), name="ops-stores"),
    path("stores/<int:pk>/open/", api.StoreOpenView.as_view(), name="ops-store-open"),
    path("applications/", api.ApplicationsView.as_view(), name="ops-applications"),
    path("applications/<int:pk>/approve/", api.ReviewApplicationView.as_view(decision="approve"), name="ops-application-approve"),
    path("applications/<int:pk>/reject/", api.ReviewApplicationView.as_view(decision="reject"), name="ops-application-reject"),
    path("users/", api.UsersView.as_view(), name="ops-users"),
    path("users/<int:pk>/active/", api.UserActiveView.as_view(), name="ops-user-active"),
]
