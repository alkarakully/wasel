from django.urls import path

from . import views

urlpatterns = [
    path("otp/request/", views.RequestCodeView.as_view(), name="otp-request"),
    path("otp/verify/", views.VerifyCodeView.as_view(), name="otp-verify"),
    path("me/", views.MeView.as_view(), name="me"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
]
