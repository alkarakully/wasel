from django.urls import path

from . import views

urlpatterns = [
    path("otp/request/", views.RequestCodeView.as_view(), name="otp-request"),
    path("otp/verify/", views.VerifyCodeView.as_view(), name="otp-verify"),
    path("password/login/", views.PasswordLoginView.as_view(), name="password-login"),
    path("password/", views.PasswordView.as_view(), name="password"),
    path("email/", views.EmailView.as_view(), name="email"),
    path("email/verify/", views.ConfirmEmailView.as_view(), name="email-verify"),
    path("me/", views.MeView.as_view(), name="me"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
]
