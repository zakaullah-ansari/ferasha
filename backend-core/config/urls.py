"""Root URL configuration for Ferasha backend-core."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .health import HealthView, ReadinessView

API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(f"{API_V1}health/", HealthView.as_view(), name="health"),
    path(f"{API_V1}ready/", ReadinessView.as_view(), name="ready"),
    path(API_V1, include("apps.users.urls", namespace="users")),
    path(API_V1, include("apps.taxes.urls", namespace="taxes")),
    path(API_V1, include("apps.catalog.urls", namespace="catalog")),
    path(API_V1, include("apps.tailoring.urls", namespace="tailoring")),
    path(API_V1, include("apps.orders.urls", namespace="orders")),
    path(API_V1, include("apps.reviews.urls", namespace="reviews")),
    path(API_V1, include("apps.media_assets.urls", namespace="media_assets")),
    # OpenAPI 3.1: the single source of truth for the generated TypeScript client.
    path(f"{API_V1}schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG or settings.EXPOSE_API_DOCS:
    urlpatterns += [
        path(
            f"{API_V1}docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            f"{API_V1}redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]

if settings.DEBUG:
    # Django's static() helper would happily serve the whole MEDIA_ROOT tree,
    # including private/originals/ - the unblurred vendor uploads. Serving
    # those over HTTP defeats the entire Phase 3 privacy pipeline, so only the
    # public derivative prefix is routed, even in DEBUG.
    #
    # In production nothing here applies: originals live in a bucket with no
    # public read policy and are reached only by presigned URL.
    urlpatterns += static(
        f"{settings.MEDIA_URL}public/",
        document_root=Path(settings.MEDIA_ROOT) / "public",
    )

admin.site.site_header = "Ferasha Administration"
admin.site.site_title = "Ferasha"
admin.site.index_title = "Atelier Operations"
