"""Catalogue serializers.

Modesty badges are serialised from the single derivation function in
apps.catalog.modesty and flow to the frontend through the OpenAPI schema. The
storefront never recomputes them in TypeScript - two implementations would
drift, and a garment displayed as "fully covered" that is not is a trust
failure, not a cosmetic bug.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.media_assets.models import ModerationStatus

from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = (
            "id", "name", "slug", "path", "depth", "parent",
            "description", "display_order", "is_active", "product_count",
        )
        read_only_fields = ("id", "path", "depth")


class CategoryTreeSerializer(CategorySerializer):
    children = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = (*CategorySerializer.Meta.fields, "children")

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj) -> list[dict]:
        children = getattr(obj, "prefetched_children", None)
        if children is None:
            children = obj.children.filter(is_active=True)
        return CategoryTreeSerializer(children, many=True, context=self.context).data


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "display_order", "is_primary")

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_url(self, obj) -> str | None:
        """Only the privacy-processed derivative is ever exposed.

        ``MediaAsset.public_url`` returns None unless the asset is APPROVED and
        blur-verified. There is deliberately no fallback to the original.
        """
        return obj.asset.public_url

    def validate_asset(self, asset):
        if asset.moderation_status != ModerationStatus.APPROVED:
            raise serializers.ValidationError(
                "This image has not cleared the privacy pipeline and cannot be published."
            )
        return asset


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id", "sku", "size", "colour", "colour_hex",
            "price", "price_delta", "in_stock", "is_active",
        )
        read_only_fields = ("id", "price")
        # stock_quantity is deliberately NOT exposed. Exact inventory levels
        # are commercially sensitive and enable scraping of sales velocity.

    @extend_schema_field(serializers.BooleanField())
    def get_in_stock(self, obj) -> bool:
        return obj.stock_quantity > 0


class ModestyBadgeSerializer(serializers.Serializer):
    """Schema shape for a derived badge. Read-only, never accepted as input."""

    code = serializers.CharField()
    label = serializers.CharField()


class ModestySerializer(serializers.Serializer):
    badges = ModestyBadgeSerializer(many=True)
    advisories = ModestyBadgeSerializer(many=True)
    coverage_score = serializers.IntegerField(min_value=0, max_value=100)


class ProductListSerializer(serializers.ModelSerializer):
    """Compact representation for grids. Kept lean - this is the hot path."""

    modesty = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    from_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "slug", "name", "category_slug", "garment_type", "fabric",
            "work_type", "occasion", "base_price", "from_price", "compare_at_price",
            "supports_bespoke", "stitching_days", "modesty", "primary_image", "status",
        )

    @extend_schema_field(ModestySerializer)
    def get_modesty(self, obj) -> dict[str, Any]:
        return obj.modesty.as_dict()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_primary_image(self, obj) -> dict | None:
        images = list(obj.images.all())
        if not images:
            return None
        primary = next((i for i in images if i.is_primary), images[0])
        url = primary.asset.public_url
        return {"url": url, "alt_text": primary.alt_text} if url else None

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_from_price(self, obj) -> Decimal:
        deltas = [v.price_delta for v in obj.variants.all() if v.is_active]
        return obj.base_price + min(deltas) if deltas else obj.base_price


class ProductDetailSerializer(ProductListSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    rating_average = serializers.FloatField(read_only=True, required=False)
    rating_count = serializers.IntegerField(read_only=True, required=False)
    fit_feedback_summary = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = (
            *ProductListSerializer.Meta.fields,
            "description", "care_instructions", "country_of_origin",
            "hsn_code", "bespoke_surcharge", "category", "variants", "images",
            "rating_average", "rating_count", "fit_feedback_summary",
            # Raw modesty attributes alongside derived badges, so the frontend
            # can render a detailed specification table.
            "is_opaque", "has_full_lining", "slit_coverage", "sleeve_coverage",
            "neckline_modesty", "back_coverage", "requires_slip",
            "is_sheer_overlay_only",
        )

    @extend_schema_field(serializers.DictField())
    def get_fit_feedback_summary(self, obj) -> dict[str, Any]:
        """Aggregated sizing guidance - the highest-value review data here."""
        from django.db.models import Count

        from apps.reviews.models import ReviewStatus

        rows = (
            obj.reviews.filter(status=ReviewStatus.PUBLISHED)
            .exclude(fit_feedback="")
            .values("fit_feedback")
            .annotate(n=Count("id"))
        )
        counts = {row["fit_feedback"]: row["n"] for row in rows}
        total = sum(counts.values())
        if not total:
            return {"total": 0, "breakdown": {}, "guidance": None}

        breakdown = {k: round(v * 100 / total) for k, v in counts.items()}
        dominant = max(counts, key=counts.get)
        guidance = {
            "ran_small": "Most customers say this runs small - consider sizing up.",
            "true_to_size": "Most customers say this is true to size.",
            "ran_large": "Most customers say this runs large - consider sizing down.",
        }.get(dominant)
        return {"total": total, "breakdown": breakdown, "guidance": guidance}


class ProductWriteSerializer(serializers.ModelSerializer):
    """Vendor/back-office product authoring.

    Modesty attributes are required on write. They are the differentiating
    facet of the catalogue and must never be left to a silent default - a
    garment mis-declared as fully covered is a trust failure.
    """

    class Meta:
        model = Product
        fields = (
            "id", "slug", "name", "category", "garment_type", "fabric", "work_type",
            "occasion", "description", "care_instructions", "country_of_origin",
            "base_price", "compare_at_price", "hsn_code", "gst_rate_override",
            "is_opaque", "has_full_lining", "slit_coverage", "sleeve_coverage",
            "neckline_modesty", "back_coverage", "requires_slip", "is_sheer_overlay_only",
            "supports_bespoke", "bespoke_surcharge", "stitching_days",
            "status", "meta_title", "meta_description",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "is_opaque": {"required": True},
            "has_full_lining": {"required": True},
            "slit_coverage": {"required": True},
            "sleeve_coverage": {"required": True},
            "neckline_modesty": {"required": True},
            "back_coverage": {"required": True},
        }

    def validate_gst_rate_override(self, value):
        if value is None:
            return value
        from apps.taxes.constants import resolve_regime

        permitted = resolve_regime().permitted_rates
        if Decimal(value) not in permitted:
            raise serializers.ValidationError(
                f"{value} is not a lawful GST rate under the regime in force. "
                f"Permitted: {sorted(str(r) for r in permitted)}."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        opaque = attrs.get("is_opaque", getattr(instance, "is_opaque", True))
        sheer = attrs.get(
            "is_sheer_overlay_only", getattr(instance, "is_sheer_overlay_only", False)
        )
        if sheer and opaque:
            raise serializers.ValidationError(
                {"is_sheer_overlay_only": "A sheer overlay cannot also be declared opaque."}
            )

        bespoke = attrs.get("supports_bespoke", getattr(instance, "supports_bespoke", False))
        days = attrs.get("stitching_days", getattr(instance, "stitching_days", 0))
        if bespoke and not days:
            raise serializers.ValidationError(
                {"stitching_days": "A bespoke product must declare an atelier lead time."}
            )

        base = attrs.get("base_price", getattr(instance, "base_price", None))
        compare = attrs.get("compare_at_price", getattr(instance, "compare_at_price", None))
        if base is not None and compare is not None and compare <= base:
            raise serializers.ValidationError(
                {"compare_at_price": "Compare-at price must exceed the selling price."}
            )
        return attrs

    def create(self, validated_data):
        # A vendor may only ever create products under their own account.
        user = self.context["request"].user
        if not user.is_back_office or "vendor" not in validated_data:
            validated_data["vendor"] = user
        return super().create(validated_data)


class ProductVariantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = (
            "id", "product", "sku", "size", "colour", "colour_hex",
            "price_delta", "stock_quantity", "low_stock_threshold",
            "weight_grams", "is_active",
        )
        read_only_fields = ("id",)

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value
