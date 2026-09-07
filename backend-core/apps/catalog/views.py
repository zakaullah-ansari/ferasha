"""Catalogue API.

Reads are public (the storefront must be crawlable and browsable without an
account); writes are restricted to the owning vendor or the back office.
"""

from __future__ import annotations

from django.db.models import Avg, Count, Prefetch, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import PublicReadBackOfficeWrite, PublicReadVendorWrite
from apps.media_assets.models import ModerationStatus
from apps.reviews.models import ReviewStatus

from .enums import ProductStatus
from .filters import ProductFilter
from .models import Category, Product, ProductImage, ProductVariant
from .serializers import (
    CategorySerializer,
    CategoryTreeSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductVariantWriteSerializer,
    ProductWriteSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List categories"),
    retrieve=extend_schema(summary="Retrieve a category"),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (PublicReadBackOfficeWrite,)
    lookup_field = "slug"

    def get_queryset(self):
        qs = Category.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_back_office):
            qs = qs.filter(is_active=True)
        return qs.order_by("display_order", "name")

    @extend_schema(summary="Category tree", responses=CategoryTreeSerializer(many=True))
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def tree(self, request):
        """Full navigation tree.

        Assembled in Python from a single flat query rather than recursing into
        the database once per level.
        """
        categories = list(self.get_queryset())
        by_parent: dict = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)
        for category in categories:
            category.prefetched_children = by_parent.get(category.id, [])
        roots = by_parent.get(None, [])
        return Response(
            CategoryTreeSerializer(roots, many=True, context={"request": request}).data
        )


@extend_schema_view(
    list=extend_schema(summary="List products with modesty facets"),
    retrieve=extend_schema(summary="Retrieve a product"),
)
class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = (PublicReadVendorWrite,)
    filterset_class = ProductFilter
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        approved_images = Prefetch(
            "images",
            queryset=ProductImage.objects.filter(
                asset__moderation_status=ModerationStatus.APPROVED
            ).select_related("asset").order_by("display_order"),
        )
        qs = (
            Product.objects.select_related("category", "vendor")
            .prefetch_related(approved_images, "variants")
            .annotate(
                rating_average=Avg(
                    "reviews__rating",
                    filter=Q(reviews__status=ReviewStatus.PUBLISHED),
                ),
                rating_count=Count(
                    "reviews",
                    filter=Q(reviews__status=ReviewStatus.PUBLISHED),
                    distinct=True,
                ),
            )
        )

        if not user.is_authenticated:
            return qs.filter(status=ProductStatus.ACTIVE)
        if user.is_back_office:
            return qs
        if getattr(user, "is_vendor", False):
            # Vendors see the whole catalogue as a customer would, plus their
            # own drafts - but never another vendor's unpublished work.
            return qs.filter(Q(status=ProductStatus.ACTIVE) | Q(vendor=user))
        return qs.filter(status=ProductStatus.ACTIVE)

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductWriteSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    @extend_schema(summary="Facet counts for the current filter set")
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def facets(self, request):
        """Counts per facet value, computed in a small fixed number of queries.

        Naive per-value counting would issue dozens of queries on the busiest
        page of the site.
        """
        qs = self.filter_queryset(self.get_queryset())

        def tally(field: str) -> dict[str, int]:
            rows = qs.values(field).annotate(n=Count("id", distinct=True))
            return {row[field]: row["n"] for row in rows if row[field]}

        return Response(
            {
                "fabric": tally("fabric"),
                "work_type": tally("work_type"),
                "occasion": tally("occasion"),
                "garment_type": tally("garment_type"),
                "slit_coverage": tally("slit_coverage"),
                "sleeve_coverage": tally("sleeve_coverage"),
                "modesty": {
                    "fully_covered": qs.fully_covered().count(),
                    "is_opaque": qs.filter(is_opaque=True).count(),
                    "has_full_lining": qs.filter(has_full_lining=True).count(),
                },
                "supports_bespoke": qs.filter(supports_bespoke=True).count(),
                "total": qs.count(),
            }
        )


class ProductVariantViewSet(viewsets.ModelViewSet):
    """Variant management. Stock levels are visible only to the back office."""

    serializer_class = ProductVariantWriteSerializer
    permission_classes = (PublicReadVendorWrite,)

    def get_queryset(self):
        user = self.request.user
        qs = ProductVariant.objects.select_related("product")
        if user.is_authenticated and user.is_back_office:
            return qs
        if user.is_authenticated and getattr(user, "is_vendor", False):
            return qs.filter(product__vendor=user)
        return qs.filter(
            is_active=True, product__status=ProductStatus.ACTIVE
        )

    def destroy(self, request, *args, **kwargs):
        variant = self.get_object()
        if variant.order_lines.exists():
            return Response(
                {
                    "detail": "This variant appears on existing orders and cannot be "
                              "deleted. Deactivate it instead."
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
