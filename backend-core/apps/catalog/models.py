"""Catalogue: categories, products, variants and imagery.

Design note - modesty attributes are stored as typed columns, not inside a
JSON blob. They are faceted-search inputs and badge drivers: they need indexes,
check constraints and aggregation, none of which jsonb provides cleanly. The
measurement data in apps.tailoring is genuinely variable in shape and *is*
stored as jsonb; these are not.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel

from .enums import (
    BackCoverage,
    Fabric,
    GarmentType,
    NecklineModesty,
    Occasion,
    ProductStatus,
    SizeStandard,
    SleeveCoverage,
    SlitCoverage,
    WorkType,
)
from .modesty import ModestyProfile, derive_modesty

hsn_validator = RegexValidator(
    regex=r"^\d{4,8}$",
    message=_("HSN/SAC codes are 4 to 8 digits."),
)


class Category(BaseModel):
    """Self-referencing merchandising tree.

    ``path`` is a materialised path ("bridal/lehenga") so a subtree read is a
    single indexed prefix query. Recursive FK traversal would issue one query
    per level on the hottest read path on the site.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    path = models.CharField(max_length=512, db_index=True, editable=False)
    depth = models.PositiveSmallIntegerField(default=0, editable=False)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    meta_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)

    class Meta:
        verbose_name_plural = _("categories")
        ordering = ("display_order", "name")
        indexes = [
            models.Index(fields=["path", "is_active"], name="category_path_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(depth__lte=4),
                name="category_depth_max_4",
            ),
        ]

    def __str__(self) -> str:
        return self.path or self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        if self.parent_id:
            parent = self.parent
            self.path = f"{parent.path}/{self.slug}"
            self.depth = parent.depth + 1
        else:
            self.path = self.slug
            self.depth = 0
        super().save(*args, **kwargs)

    def descendants(self):
        """All categories beneath this one, in a single query."""
        return Category.objects.filter(path__startswith=f"{self.path}/")

    def self_and_descendants(self):
        return Category.objects.filter(
            models.Q(pk=self.pk) | models.Q(path__startswith=f"{self.path}/")
        )


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=ProductStatus.ACTIVE)

    def purchasable(self):
        """Active products with at least one variant in stock."""
        return self.active().filter(variants__stock_quantity__gt=0).distinct()

    def fully_covered(self):
        """Products qualifying for the FULL_COVERAGE badge.

        Mirrors apps.catalog.modesty.derive_modesty. A test asserts the two
        agree on every product, so this cannot silently drift.
        """
        return self.filter(
            is_opaque=True,
            has_full_lining=True,
            is_sheer_overlay_only=False,
            requires_slip=False,
            sleeve_coverage__in=[SleeveCoverage.FULL, SleeveCoverage.EXTRA_LONG],
            slit_coverage__in=[SlitCoverage.NONE, SlitCoverage.ANKLE],
            neckline_modesty__in=[NecklineModesty.HIGH, NecklineModesty.CLOSED],
            back_coverage__in=[BackCoverage.MODERATE, BackCoverage.FULL],
        )


class Product(BaseModel):
    """A sellable garment or dress material."""

    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="products",
        limit_choices_to={"role__in": ["vendor", "staff", "admin"]},
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    garment_type = models.CharField(max_length=24, choices=GarmentType.choices, db_index=True)
    fabric = models.CharField(max_length=16, choices=Fabric.choices, db_index=True)
    work_type = models.CharField(
        max_length=16, choices=WorkType.choices, default=WorkType.PLAIN, db_index=True
    )
    occasion = models.CharField(max_length=12, choices=Occasion.choices, db_index=True)

    description = models.TextField(blank=True)
    care_instructions = models.TextField(blank=True)
    country_of_origin = models.CharField(max_length=2, default="IN")

    # --- Pricing & tax ------------------------------------------------------
    base_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    compare_at_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text=_("Strike-through price. Must exceed base_price when set."),
    )
    hsn_code = models.CharField(max_length=8, validators=[hsn_validator], db_index=True)
    gst_rate_override = models.DecimalField(
        max_digits=4, decimal_places=0, null=True, blank=True,
        help_text=_("Only where the HSN slab genuinely does not apply. Validated "
                    "against the GST regime in force."),
    )

    # --- Modesty attributes (typed columns, deliberately not JSON) ----------
    is_opaque = models.BooleanField(
        default=True, db_index=True, help_text=_("Fabric is not see-through.")
    )
    has_full_lining = models.BooleanField(default=False, db_index=True)
    slit_coverage = models.CharField(
        max_length=10, choices=SlitCoverage.choices, default=SlitCoverage.NONE, db_index=True
    )
    sleeve_coverage = models.CharField(
        max_length=14, choices=SleeveCoverage.choices, default=SleeveCoverage.FULL, db_index=True
    )
    neckline_modesty = models.CharField(
        max_length=10, choices=NecklineModesty.choices, default=NecklineModesty.MODERATE
    )
    back_coverage = models.CharField(
        max_length=10, choices=BackCoverage.choices, default=BackCoverage.FULL
    )
    requires_slip = models.BooleanField(default=False)
    is_sheer_overlay_only = models.BooleanField(default=False)

    # --- Bespoke ------------------------------------------------------------
    supports_bespoke = models.BooleanField(default=False, db_index=True)
    bespoke_surcharge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stitching_days = models.PositiveSmallIntegerField(
        default=0, help_text=_("Atelier lead time in days for a bespoke order.")
    )

    status = models.CharField(
        max_length=16, choices=ProductStatus.choices, default=ProductStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)

    meta_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "category"], name="product_status_cat_idx"),
            models.Index(
                fields=["is_opaque", "has_full_lining", "slit_coverage"],
                name="product_modesty_facet_idx",
            ),
            models.Index(fields=["occasion", "status"], name="product_occasion_idx"),
            models.Index(fields=["base_price"], name="product_price_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_price__gte=Decimal("0.00")),
                name="product_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(bespoke_surcharge__gte=Decimal("0.00")),
                name="product_bespoke_surcharge_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(compare_at_price__isnull=True)
                | models.Q(compare_at_price__gt=models.F("base_price")),
                name="product_compare_at_exceeds_base",
            ),
            # A bespoke product with a zero lead time is an operational lie.
            models.CheckConstraint(
                condition=models.Q(supports_bespoke=False) | models.Q(stitching_days__gt=0),
                name="product_bespoke_requires_lead_time",
            ),
            # A sheer overlay cannot also be claimed as opaque.
            models.CheckConstraint(
                condition=models.Q(is_sheer_overlay_only=False) | models.Q(is_opaque=False),
                name="product_sheer_overlay_not_opaque",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    slit_coverage__in=[c[0] for c in SlitCoverage.choices]
                ),
                name="product_slit_coverage_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    sleeve_coverage__in=[c[0] for c in SleeveCoverage.choices]
                ),
                name="product_sleeve_coverage_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    neckline_modesty__in=[c[0] for c in NecklineModesty.choices]
                ),
                name="product_neckline_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(back_coverage__in=[c[0] for c in BackCoverage.choices]),
                name="product_back_coverage_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[c[0] for c in ProductStatus.choices]),
                name="product_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        self.country_of_origin = self.country_of_origin.upper()
        super().save(*args, **kwargs)

    # -- Modesty -------------------------------------------------------------
    @property
    def modesty_profile(self) -> ModestyProfile:
        return ModestyProfile(
            is_opaque=self.is_opaque,
            has_full_lining=self.has_full_lining,
            slit_coverage=self.slit_coverage,
            sleeve_coverage=self.sleeve_coverage,
            neckline_modesty=self.neckline_modesty,
            back_coverage=self.back_coverage,
            requires_slip=self.requires_slip,
            is_sheer_overlay_only=self.is_sheer_overlay_only,
        )

    @property
    def modesty(self):
        return derive_modesty(self.modesty_profile)

    @property
    def in_stock(self) -> bool:
        return any(v.stock_quantity > 0 for v in self.variants.all())


class ProductVariant(BaseModel):
    """A purchasable size/colour combination."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    size = models.CharField(max_length=8, choices=SizeStandard.choices)
    colour = models.CharField(max_length=60)
    colour_hex = models.CharField(max_length=7, blank=True)

    price_delta = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text=_("Added to the product base price. May be negative."),
    )
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=2)
    weight_grams = models.PositiveIntegerField(
        default=0, help_text=_("Used for shipping rate calculation.")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("product", "size", "colour")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "colour"], name="unique_variant_per_product"
            ),
            # The guarantee against overselling. Any code path that would drive
            # stock below zero fails at the database, not merely in Python.
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name="variant_stock_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(size__in=[c[0] for c in SizeStandard.choices]),
                name="variant_size_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_active"], name="variant_product_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sku} ({self.size}/{self.colour})"

    @property
    def price(self) -> Decimal:
        return self.product.base_price + self.price_delta

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock_quantity <= self.low_stock_threshold


class ProductImage(BaseModel):
    """Ordered imagery for a product.

    The image itself lives in apps.media_assets, which owns the Phase 3 privacy
    pipeline. Only an APPROVED asset may be attached here - enforced by
    ProductImage.clean() and by a serializer check, so an unblurred original
    cannot reach the storefront through this relation.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    asset = models.ForeignKey(
        "media_assets.MediaAsset", on_delete=models.PROTECT, related_name="product_images"
    )
    alt_text = models.CharField(max_length=200)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ("display_order",)
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} #{self.display_order}"

    def clean(self):
        from django.core.exceptions import ValidationError

        from apps.media_assets.models import ModerationStatus

        super().clean()
        if self.asset_id and self.asset.moderation_status != ModerationStatus.APPROVED:
            raise ValidationError(
                {
                    "asset": _(
                        "Only media that has passed the privacy pipeline may be "
                        "published. This asset is %(status)s."
                    )
                    % {"status": self.asset.get_moderation_status_display()}
                }
            )
