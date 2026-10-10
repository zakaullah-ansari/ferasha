"""Review API."""

from __future__ import annotations

from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import IsOwnerOrBackOffice
from apps.media_assets.models import ModerationStatus

from .models import Review, ReviewPhoto, ReviewStatus
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_fields = ("product", "rating", "fit_feedback")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return []
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsOwnerOrBackOffice()]

    def get_queryset(self):
        approved_photos = Prefetch(
            "photos",
            queryset=ReviewPhoto.objects.filter(
                asset__moderation_status=ModerationStatus.APPROVED
            ).select_related("asset"),
        )
        qs = Review.objects.select_related("author", "product").prefetch_related(
            approved_photos
        )

        user = self.request.user
        if user.is_authenticated and user.is_back_office:
            return qs
        if user.is_authenticated:
            # Your own pending review remains visible to you while it is
            # in the moderation queue.
            from django.db.models import Q

            return qs.filter(Q(status=ReviewStatus.PUBLISHED) | Q(author=user))
        return qs.filter(status=ReviewStatus.PUBLISHED)
