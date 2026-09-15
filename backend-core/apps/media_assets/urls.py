"""URLs for AI-engine media callbacks."""

from __future__ import annotations

from django.urls import path

from .views import MediaCallbackView, MediaDerivativeUploadView

app_name = "media_assets"

urlpatterns = [
    path("media/callback/", MediaCallbackView.as_view(), name="callback"),
    path(
        "media/<uuid:asset_id>/derivative/",
        MediaDerivativeUploadView.as_view(),
        name="derivative-upload",
    ),
]
