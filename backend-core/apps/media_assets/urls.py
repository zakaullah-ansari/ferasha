"""URLs the AI-engine worker talks to: fetch the original, upload the blur, report."""

from __future__ import annotations

from django.urls import path

from .views import MediaCallbackView, MediaDerivativeUploadView, MediaOriginalDownloadView

app_name = "media_assets"

urlpatterns = [
    path("media/callback/", MediaCallbackView.as_view(), name="callback"),
    path(
        "media/<uuid:asset_id>/derivative/",
        MediaDerivativeUploadView.as_view(),
        name="derivative-upload",
    ),
    path(
        "media/<uuid:asset_id>/original/",
        MediaOriginalDownloadView.as_view(),
        name="original",
    ),
]
