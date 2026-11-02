"""Review moderation."""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import Review, ReviewStatus


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("product", "author", "rating", "status_badge", "modesty_as_described", "created_at")
    list_filter = ("status", "rating", "fit_feedback", "modesty_as_described")
    search_fields = ("title", "body", "product__name", "author__email")
    list_select_related = ("product", "author")
    actions = ("publish", "reject")
    readonly_fields = (
        "product", "author", "order_line", "rating", "title", "body", "fit_feedback",
        "modesty_as_described", "helpful_count", "moderated_by", "moderated_at",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False  # reviews are written by customers

    @display(
        description=_("Status"),
        ordering="status",
        label={
            ReviewStatus.PENDING.label: "warning",
            ReviewStatus.PUBLISHED.label: "success",
            ReviewStatus.REJECTED.label: "danger",
        },
    )
    def status_badge(self, obj: Review) -> str:
        return obj.get_status_display()

    def _moderate(self, request, queryset, status: str) -> int:
        return queryset.update(status=status, moderated_by=request.user, moderated_at=timezone.now())

    @action(description=_("Publish selected reviews"))
    def publish(self, request, queryset):
        count = self._moderate(request, queryset, ReviewStatus.PUBLISHED)
        messages.success(request, _("%(count)d review(s) published.") % {"count": count})

    @action(description=_("Reject selected reviews"))
    def reject(self, request, queryset):
        count = self._moderate(request, queryset, ReviewStatus.REJECTED)
        messages.success(request, _("%(count)d review(s) rejected.") % {"count": count})
