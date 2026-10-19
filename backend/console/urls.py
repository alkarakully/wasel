from django.urls import path

from . import api_money as money
from . import api_orders as orders
from . import api_people as people
from . import api_stores as stores
from . import auth_api as auth

urlpatterns = [
    # Sign-in
    path("auth/session/", auth.SessionView.as_view()),
    path("auth/login/", auth.LoginView.as_view()),
    path("auth/verify/", auth.VerifyView.as_view()),
    path("auth/logout/", auth.LogoutView.as_view()),
    path("auth/password/", auth.PasswordView.as_view()),
    # Overview, orders and dispatch
    path("overview/", orders.OverviewView.as_view()),
    path("orders/", orders.OrdersView.as_view()),
    path("orders/<int:pk>/", orders.OrderView.as_view()),
    path("orders/<int:pk>/cancel/", orders.CancelOrderView.as_view()),
    path("orders/<int:pk>/release/", orders.ReleaseCaptainView.as_view()),
    path("orders/<int:pk>/dispatch/", orders.DispatchView.as_view()),
    path("alerts/", orders.AlertsView.as_view()),
    path("alerts/<int:pk>/resolve/", orders.ResolveAlertView.as_view()),
    path("map/", orders.CaptainsMapView.as_view()),
    # Stores, menus and teams
    path("stores/", stores.StoresView.as_view()),
    path("stores/choices/", money.StoreChoicesView.as_view()),
    path("stores/<int:pk>/", stores.StoreView.as_view()),
    path("stores/<int:pk>/review/", stores.StoreReviewView.as_view()),
    path("stores/<int:pk>/menu/", stores.StoreMenuView.as_view()),
    path("products/<int:pk>/", stores.ProductView.as_view()),
    path("stores/<int:pk>/team/", stores.StoreTeamView.as_view()),
    path("stores/<int:pk>/team/<int:member_id>/", stores.StoreMemberView.as_view()),
    # People
    path("users/", people.UsersView.as_view()),
    path("users/<int:pk>/", people.UserView.as_view()),
    path("users/<int:pk>/active/", people.UserActiveView.as_view()),
    path("users/<int:pk>/wallet/", people.WalletAdjustView.as_view()),
    path("staff/", people.StaffListView.as_view()),
    path("staff/<int:pk>/", people.StaffMemberView.as_view()),
    path("staff/<int:pk>/reset/", people.StaffResetView.as_view()),
    path("audit/", people.AuditView.as_view()),
    # Money and marketing
    path("payouts/", money.PayoutsView.as_view()),
    path("payouts/close/", money.CloseWeeksView.as_view()),
    path("payouts/<int:pk>/paid/", money.PayoutPaidView.as_view()),
    path("wallet/", money.WalletView.as_view()),
    path("reports/", money.ReportsView.as_view()),
    path("offers/", money.OffersView.as_view()),
    path("offers/<int:pk>/", money.OfferView.as_view()),
    path("plus/", money.PlusView.as_view()),
]
