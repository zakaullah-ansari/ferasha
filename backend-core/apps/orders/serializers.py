"""Order serializers. Read-mostly at this phase; checkout lands in Phase 5."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.tailoring.serializers import TailoringOrderSpecSerializer

from .models import Order, OrderEvent, OrderLine, OrderTaxSnapshot
from .state_machine import available_transitions


class OrderLineSerializer(serializers.ModelSerializer):
    tailoring_spec = TailoringOrderSpecSerializer(read_only=True)
    gross = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderLine
        fields = (
            "id", "sku", "product_name", "variant_label", "hsn_code",
            "quantity", "unit_price", "discount", "gross",
            "is_bespoke", "modesty_snapshot", "tailoring_spec",
        )
        read_only_fields = fields


class OrderTaxSnapshotSerializer(serializers.ModelSerializer):
    """The tax as issued. Read-only everywhere - an invoice is not editable."""

    class Meta:
        model = OrderTaxSnapshot
        fields = (
            "regime_name", "supply_type", "place_of_supply_state",
            "place_of_supply_country", "state_gst_code",
            "taxable_value", "cgst_total", "sgst_total", "igst_total",
            "tax_total", "grand_total", "is_zero_rated_export",
            "line_breakdown", "rate_summary", "notes",
        )
        read_only_fields = fields


class OrderEventSerializer(serializers.ModelSerializer):
    """Back-office view of the audit trail, including who acted and why."""

    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default="")

    class Meta:
        model = OrderEvent
        fields = ("id", "from_status", "to_status", "actor_name", "reason", "created_at")
        read_only_fields = fields


class CustomerOrderEventSerializer(serializers.ModelSerializer):
    """Customer-facing timeline.

    Deliberately narrower than the back-office serializer: ``actor_name``
    identifies internal staff and ``reason`` is free text written for internal
    consumption ("customer chargeback risk", "fabric shortage - reorder"). Both
    are withheld. The status transitions themselves are the customer's record.
    """

    class Meta:
        model = OrderEvent
        fields = ("id", "from_status", "to_status", "created_at")
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    line_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "status", "currency", "grand_total",
            "line_count", "placed_at", "created_at",
        )
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    tax_snapshot = OrderTaxSnapshotSerializer(read_only=True)
    events = serializers.SerializerMethodField()
    next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "status", "currency",
            "place_of_supply_state", "place_of_supply_country", "supply_type",
            "supply_date", "shipping_address", "billing_address", "customer_gstin",
            "subtotal", "discount_total", "shipping_charge", "tax_total", "grand_total",
            "lines", "tax_snapshot", "events", "next_statuses",
            "customer_notes", "placed_at", "delivered_at", "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(OrderEventSerializer(many=True))
    def get_events(self, obj):
        """Customers see their own order's timeline; internal notes stay internal."""
        request = self.context.get("request")
        events = obj.events.all().order_by("-created_at")
        if request and request.user.is_authenticated and request.user.is_back_office:
            return OrderEventSerializer(events, many=True).data
        return CustomerOrderEventSerializer(events, many=True).data

    def get_next_statuses(self, obj) -> list[str]:
        request = self.context.get("request")
        if not (request and request.user.is_authenticated and request.user.is_back_office):
            return []
        return sorted(available_transitions(obj.status))
