from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CheckoutViewSet

router = DefaultRouter()
router.register("checkout", CheckoutViewSet, basename="checkout")

app_name = "checkout"

urlpatterns = [path("", include(router.urls))]
