"""Serializers wrapping the pure-Python GST engine for HTTP exposure."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from rest_framework import serializers

from .constants import resolve_regime
from .services import PlaceOfSupply, TaxableLine, TaxError, calculate_gst


class TaxableLineSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=64)
    hsn_code = serializers.CharField(max_length=16)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    quantity = serializers.IntegerField(min_value=1, default=1)
    discount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0.00")
    )
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    rate_override = serializers.DecimalField(
        max_digits=4, decimal_places=0, required=False, allow_null=True, default=None
    )
    price_is_tax_inclusive = serializers.BooleanField(default=False)

    def validate_rate_override(self, value: Decimal | None) -> Decimal | None:
        """Validated against the regime in force; the engine re-checks per line."""
        if value is None:
            return value
        permitted = resolve_regime().permitted_rates
        if Decimal(value) not in permitted:
            raise serializers.ValidationError(
                f"{value} is not a lawful GST rate. Permitted: {sorted(permitted)}."
            )
        return value


class TaxQuoteRequestSerializer(serializers.Serializer):
    """Request body for POST /api/v1/tax/quote/."""

    country_code = serializers.CharField(max_length=2, default="IN")
    state_code = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")
    shipping_charge = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0.00")
    )
    as_of = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Date of supply. Selects the GST regime. Defaults to today.",
    )
    lines = TaxableLineSerializer(many=True, allow_empty=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        try:
            place = PlaceOfSupply(
                country_code=attrs["country_code"], state_code=attrs.get("state_code", "")
            )
        except TaxError as exc:
            raise serializers.ValidationError({"place_of_supply": str(exc)}) from exc

        as_of: date | None = attrs.get("as_of")
        try:
            lines = [TaxableLine(**line, as_of=as_of) for line in attrs["lines"]]
        except TaxError as exc:
            raise serializers.ValidationError({"lines": str(exc)}) from exc
        except ValueError as exc:
            raise serializers.ValidationError({"as_of": str(exc)}) from exc

        attrs["_place_of_supply"] = place
        attrs["_lines"] = lines
        return attrs

    def quote(self) -> dict[str, Any]:
        data = self.validated_data
        try:
            breakdown = calculate_gst(
                data["_lines"],
                data["_place_of_supply"],
                shipping_charge=data["shipping_charge"],
                as_of=data.get("as_of"),
            )
        except TaxError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return breakdown.as_dict()
