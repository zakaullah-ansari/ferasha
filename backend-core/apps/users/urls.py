"""URL routes for the identity app."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    AddressViewSet,
    CurrentUserView,
    EmailVerificationConfirmView,
    EmailVerificationRequestView,
    FerashaTokenObtainPairView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegistrationView,
)

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")

app_name = "users"

urlpatterns = [
    path("auth/register/", RegistrationView.as_view(), name="register"),
    path("auth/token/", FerashaTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password-change"),
    path(
        "auth/password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "auth/email/verify/request/",
        EmailVerificationRequestView.as_view(),
        name="email-verify-request",
    ),
    path(
        "auth/email/verify/confirm/",
        EmailVerificationConfirmView.as_view(),
        name="email-verify-confirm",
    ),
    path("", include(router.urls)),
]
