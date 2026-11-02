"""Media admin: the privacy pipeline's results, view only.

Approval belongs to the pipeline (face detection + verified blur); there is no
human-approval path in the model yet, so none is improvised here.
"""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.decorators import display

from apps.common.admin import ReadOnlyAdmin

from .models import MediaAsset, ModerationStatus


@admin.register(MediaAsset)
class MediaAssetAdmin(ReadOnlyAdmin):
    list_display = ("__str__", "kind", "moderation_badge", "faces_detected", "blur_verified", "created_at")
    list_filter = ("moderation_status", "kind", "blur_verified")
    search_fields = ("id", "checksum", "uploaded_by__email")
    exclude = ("original",)  # the unblurred upload is never shown in the admin

    @display(
        description=_("Moderation"),
        ordering="moderation_status",
        label={
            ModerationStatus.APPROVED.label: "success",
            ModerationStatus.NEEDS_REVIEW.label: "warning",
            ModerationStatus.PENDING.label: "info",
            ModerationStatus.PROCESSING.label: "info",
            ModerationStatus.REJECTED.label: "danger",
            ModerationStatus.FAILED.label: "danger",
        },
    )
    def moderation_badge(self, obj: MediaAsset) -> str:
        return obj.get_moderation_status_display()

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        # The product-image picker (autocomplete) offers only assets that may be
        # published, instead of listing everything and refusing on save.
        if request.GET.get("model_name") == "productimage":
            queryset = queryset.filter(moderation_status=ModerationStatus.APPROVED)
        return queryset, may_have_duplicates
