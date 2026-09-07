"""Root URL configuration for Ferasha backend-core."""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .health import HealthView, ReadinessView

API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(f"{API_V1}health/", HealthView.as_view(), name="health"),
    path(f"{API_V1}ready/", ReadinessView.as_view(), name="ready"),
    path(API_V1, include("apps.users.urls", namespace="users")),
    path(API_V1, include("apps.taxes.urls", namespace="taxes")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Ferasha Administration"
admin.site.site_title = "Ferasha"
admin.site.index_title = "Atelier Operations"
