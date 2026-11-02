"""Catalogue admin: products with their variants and images, stock, categories."""

from __future__ import annotations

from django.contrib import admin
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .enums import ProductStatus
from .models import Category, Product, ProductImage, ProductVariant
from .services import sync_face_coverage


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("sku", "size", "colour", "colour_hex", "price_delta", "stock_quantity", "is_active")


class ProductImageInline(TabularInline):
    """Only approved (face-blurred) assets can be attached: ProductImage.clean
    refuses anything the privacy pipeline has not passed."""

    model = ProductImage
    extra = 0
    fields = ("asset", "alt_text", "display_order", "is_primary")
    autocomplete_fields = ("asset",)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "status_badge", "garment_type", "base_price", "stock_total", "supports_bespoke")
    list_filter = ("status", "garment_type", "fabric", "occasion", "supports_bespoke", "face_coverage")
    search_fields = ("name", "slug", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("vendor", "category")
    readonly_fields = ("modesty_summary", "created_at", "updated_at")
    inlines = (ProductVariantInline, ProductImageInline)
    list_per_page = 50

    fieldsets = (
        (None, {"fields": ("name", "slug", "status", "published_at", "vendor", "category")}),
        (_("Garment"), {
            "fields": ("garment_type", "fabric", "work_type", "occasion", "description",
                       "care_instructions", "country_of_origin"),
        }),
        (_("Price & GST"), {
            "fields": ("base_price", "compare_at_price", "hsn_code", "gst_rate_override"),
        }),
        (_("Modesty & coverage"), {
            "description": _("Badges are derived from these answers. Answer conservatively: "
                             "over-claiming coverage loses a customer for good."),
            "fields": ("modesty_summary", "is_opaque", "has_full_lining", "slit_coverage",
                       "sleeve_coverage", "neckline_modesty", "back_coverage", "face_coverage",
                       "requires_slip", "is_sheer_overlay_only"),
        }),
        (_("Bespoke tailoring"), {"fields": ("supports_bespoke", "bespoke_surcharge", "stitching_days")}),
        (_("Search engines"), {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
        (_("Record"), {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_stock=Sum("variants__stock_quantity"))

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Images may have been added or removed: re-derive the face-modesty
        # badge from them rather than trusting the form's value.
        sync_face_coverage(form.instance)

    @display(
        description=_("Status"),
        ordering="status",
        label={
            ProductStatus.ACTIVE.label: "success",
            ProductStatus.DRAFT.label: "info",
            ProductStatus.PENDING_REVIEW.label: "info",
            ProductStatus.OUT_OF_STOCK.label: "warning",
            ProductStatus.ARCHIVED.label: "danger",
        },
    )
    def status_badge(self, obj: Product):
        return obj.get_status_display()

    @display(description=_("In stock"), ordering="_stock")
    def stock_total(self, obj: Product) -> int:
        return obj._stock or 0

    @display(description=_("Modesty badges shown to customers"))
    def modesty_summary(self, obj: Product) -> str:
        if not obj.pk:
            return "-"
        assessment = obj.modesty.as_dict()
        badges = ", ".join(b["label"] for b in assessment["badges"]) or "none"
        advisories = ", ".join(a["label"] for a in assessment["advisories"]) or "none"
        return f"Badges: {badges}. Advisories: {advisories}. Coverage {assessment['coverage_score']}/100."


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    """Stock at a glance; quantities editable straight from the list."""

    list_display = ("sku", "product", "size", "colour", "stock_quantity", "low_stock", "is_active")
    list_editable = ("stock_quantity", "is_active")
    list_filter = ("is_active", "size", "product__status")
    search_fields = ("sku", "product__name", "colour")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    ordering = ("stock_quantity", "sku")

    @display(description=_("Low stock"), boolean=True)
    def low_stock(self, obj: ProductVariant) -> bool:
        return obj.is_low_stock or obj.stock_quantity == 0


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "parent", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent",)
    readonly_fields = ("path", "depth")
