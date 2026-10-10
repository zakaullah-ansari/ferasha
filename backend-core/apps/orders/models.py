"""Orders, lines, tax snapshots and the audit trail.

Two invariants drive this module:

1. **The tax breakdown is snapshotted at checkout and never recomputed.**
   Rates change - GST 2.0 in September 2025 moved premium apparel from 12% to
   18% - and an invoice is a legal document. Recomputing on read would silently
   alter a customer's issued invoice after a Budget.

2. **Every state change is recorded.** A bespoke order passes through many
   hands; "who marked this shipped" must always be answerable.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class OrderStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PLACED = "placed", _("Placed")
    PAYMENT_CONFIRMED = "payment_confirmed", _("Payment confirmed")
    IN_ATELIER = "in_atelier", _("In atelier")
    MEASUREMENT_REVIEW = "measurement_review", _("Measurement review")
    STITCHING = "stitching", _("Stitching")
    QUALITY_CHECK = "quality_check", _("Quality check")
    PACKED = "packed", _("Packed")
    SHIPPED = "shipped", _("Shipped")
    DELIVERED = "delivered", _("Delivered")
    RETURN_REQUESTED = "return_requested", _("Return requested")
    RETURNED = "returned", _("Returned")
    REFUNDED = "refunded", _("Refunded")
    CANCELLED = "cancelled", _("Cancelled")


class SupplyType(models.TextChoices):
    INTRA_STATE = "intra_state", _("Intra-state (CGST + SGST)")
    INTER_STATE = "inter_state", _("Inter-state (IGST)")
    EXPORT = "export", _("Zero-rated export")


class Order(BaseModel):
    """An order header. Place of supply and supply date are frozen at placement."""

    order_number = models.CharField(max_length=24, unique=True, db_index=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text=_("Null for guest checkout."),
    )
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=16, blank=True)

    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT, db_index=True
    )

    # --- Frozen tax context -------------------------------------------------
    # Copied from the shipping address at placement. If the customer later
    # edits that address, this order's tax treatment must not change.
    place_of_supply_state = models.CharField(max_length=8, blank=True)
    place_of_supply_country = models.CharField(max_length=2, default="IN")
    supply_type = models.CharField(max_length=12, choices=SupplyType.choices, blank=True)
    supply_date = models.DateField(
        null=True, blank=True,
        help_text=_("Date of supply. Selects the GST regime for this order forever."),
    )

    # --- Addresses (denormalised copies, not FKs) ---------------------------
    # An address row can be edited or deleted; the order's shipping details are
    # part of the contract and must remain exactly as they were.
    shipping_address = models.JSONField(default=dict)
    billing_address = models.JSONField(default=dict)
    customer_gstin = models.CharField(max_length=15, blank=True)

    # --- Money --------------------------------------------------------------
    currency = models.CharField(max_length=3, default="INR")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    placed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "-created_at"], name="order_status_created_idx"),
            models.Index(fields=["customer", "-created_at"], name="order_customer_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[c[0] for c in OrderStatus.choices]),
                name="order_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(grand_total__gte=Decimal("0.00")),
                name="order_grand_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_total__gte=Decimal("0.00")),
                name="order_discount_non_negative",
            ),
            # Either an account or guest contact details - never neither, or
            # the order is unreachable.
            models.CheckConstraint(
                condition=models.Q(customer__isnull=False) | ~models.Q(guest_email=""),
                name="order_has_customer_or_guest_email",
            ),
        ]

    def __str__(self) -> str:
        return self.order_number

    @property
    def contact_email(self) -> str:
        return self.customer.email if self.customer_id else self.guest_email

    @property
    def is_guest(self) -> bool:
        return self.customer_id is None

    @property
    def has_bespoke_items(self) -> bool:
        return self.lines.filter(is_bespoke=True).exists()


class OrderLine(BaseModel):
    """A single purchased item.

    Product details are denormalised onto the line: a product can be renamed,
    repriced or archived, but the order must render exactly as purchased.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, on_delete=models.SET_NULL, related_name="order_lines"
    )

    sku = models.CharField(max_length=64)
    product_name = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=120, blank=True)
    hsn_code = models.CharField(max_length=8)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    is_bespoke = models.BooleanField(default=False, db_index=True)

    #: Modesty attributes as sold. If a product's attributes are later
    #: corrected, a dispute about what was advertised is still answerable.
    modesty_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="orderline_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=Decimal("0.00")),
                name="orderline_unit_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount__gte=Decimal("0.00")),
                name="orderline_discount_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} x{self.quantity}"

    @property
    def gross(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderTaxSnapshot(BaseModel):
    """The GST computation as issued, frozen forever.

    This is the source of truth for the invoice, for GST returns, and for any
    later credit note. It is written once at checkout inside the same
    transaction as the order and is never updated.
    """

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="tax_snapshot")

    #: Name of the GST regime applied, e.g. "GST 2.0 (56th Council, ...)".
    regime_name = models.CharField(max_length=120)
    supply_type = models.CharField(max_length=12, choices=SupplyType.choices)
    place_of_supply_state = models.CharField(max_length=8, blank=True)
    place_of_supply_country = models.CharField(max_length=2)
    state_gst_code = models.CharField(max_length=4, blank=True)

    taxable_value = models.DecimalField(max_digits=12, decimal_places=2)
    cgst_total = models.DecimalField(max_digits=12, decimal_places=2)
    sgst_total = models.DecimalField(max_digits=12, decimal_places=2)
    igst_total = models.DecimalField(max_digits=12, decimal_places=2)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    is_zero_rated_export = models.BooleanField(default=False)

    #: Full per-line breakdown from apps.taxes.services.TaxBreakdown.as_dict().
    line_breakdown = models.JSONField()
    rate_summary = models.JSONField(default=list)
    notes = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tax_total__gte=Decimal("0.00")),
                name="taxsnapshot_tax_non_negative",
            ),
            # Arithmetic integrity, enforced by the database.
            models.CheckConstraint(
                condition=models.Q(
                    tax_total=models.F("cgst_total")
                    + models.F("sgst_total")
                    + models.F("igst_total")
                ),
                name="taxsnapshot_components_sum_to_total",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    grand_total=models.F("taxable_value") + models.F("tax_total")
                ),
                name="taxsnapshot_grand_total_consistent",
            ),
            # An export is zero-rated by definition.
            models.CheckConstraint(
                condition=~models.Q(is_zero_rated_export=True)
                | models.Q(tax_total=Decimal("0.00")),
                name="taxsnapshot_export_is_zero_rated",
            ),
        ]

    def __str__(self) -> str:
        return f"Tax for {self.order.order_number}: {self.tax_total}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            existing = OrderTaxSnapshot.objects.filter(pk=self.pk).exists()
            if existing:
                raise ValueError(
                    "OrderTaxSnapshot is immutable. An issued invoice's tax cannot be "
                    "altered; raise a credit note instead."
                )
        super().save(*args, **kwargs)


class OrderEvent(models.Model):
    """Append-only audit trail of order state changes."""

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=300, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["order", "-created_at"], name="orderevent_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order_id}: {self.from_status or '-'} -> {self.to_status}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("OrderEvent is append-only and cannot be modified.")
        super().save(*args, **kwargs)
