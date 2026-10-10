from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductVariantViewSet, ProductViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("variants", ProductVariantViewSet, basename="variant")

app_name = "catalog"

urlpatterns = [path("catalog/", include(router.urls))]
