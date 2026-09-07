from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

app_name = "orders"

urlpatterns = [path("", include(router.urls))]
