from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartViewSet

router = DefaultRouter()
router.register("cart", CartViewSet, basename="cart")

app_name = "cart"

urlpatterns = [path("", include(router.urls))]
