"""Review API."""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, Prefetch, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOwnerOrBackOffice
from apps.media_assets.models import ModerationStatus

from .models import FitFeedback, Review, ReviewPhoto, ReviewStatus
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_fields = ("product", "rating", "fit_feedback")

    def get_permissions(self):
        if self.action in {"list", "retrieve", "summary"}:
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

    @extend_schema(summary="Rating, fit and coverage summary of a product's published reviews")
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """What a product page shows above its reviews, in one query.

        Published reviews only: a review in the moderation queue counts for
        nothing until the atelier has read it.
        """
        try:
            product = uuid.UUID(request.query_params.get("product", ""))
        except ValueError:
            return Response({"product": ["A product id is required."]}, status=status.HTTP_400_BAD_REQUEST)

        published = Review.objects.filter(product=product, status=ReviewStatus.PUBLISHED)
        totals = published.aggregate(
            count=Count("id"),
            average=Avg("rating"),
            **{f"stars_{n}": Count("id", filter=Q(rating=n)) for n in range(1, 6)},
            **{f"fit_{value}": Count("id", filter=Q(fit_feedback=value)) for value in FitFeedback.values},
            modest_yes=Count("id", filter=Q(modesty_as_described=True)),
            modest_no=Count("id", filter=Q(modesty_as_described=False)),
        )
        average = totals["average"]
        return Response(
            {
                "count": totals["count"],
                "average": str(Decimal(average).quantize(Decimal("0.1"), ROUND_HALF_UP)) if average is not None else None,
                "distribution": {str(n): totals[f"stars_{n}"] for n in range(1, 6)},
                "fit": {value: totals[f"fit_{value}"] for value in FitFeedback.values},
                "modesty_as_described": {"yes": totals["modest_yes"], "no": totals["modest_no"]},
            }
        )
