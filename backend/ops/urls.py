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
    path("users/", api.UsersView.as_view(), name="ops-users"),
    path("users/<int:pk>/active/", api.UserActiveView.as_view(), name="ops-user-active"),
]
