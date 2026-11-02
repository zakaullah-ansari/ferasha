from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.users.models import Address


class DeliveryAddressSerializer(serializers.ModelSerializer):
    """An address as it is frozen onto an order.

    Built on ``users.Address`` so phone and GSTIN validation are the model's
    own, not a second copy that could drift.
    """

    class Meta:
        model = Address
        fields = (
            "recipient_name", "phone", "line1", "line2", "city",
            "state_code", "postal_code", "country_code", "gstin",
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Mirror Address.save()'s normalisation so the snapshot matches what a
        # saved address would have stored.
        for key in ("state_code", "country_code", "gstin"):
            attrs[key] = (attrs.get(key) or "").upper().strip()
        attrs.setdefault("line2", "")
        return attrs


class CheckoutRequestSerializer(serializers.Serializer):
    """Either a saved ``address_id`` or an inline ``address``, never both."""

    address_id = serializers.UUIDField(required=False)
    address = DeliveryAddressSerializer(required=False)
    expected_grand_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    customer_notes = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        has_id, has_inline = "address_id" in attrs, "address" in attrs
        if has_id == has_inline:
            raise serializers.ValidationError(
                "Provide exactly one of address_id or address."
            )
        if has_id:
            user = self.context["request"].user
            saved = Address.objects.filter(pk=attrs.pop("address_id"), user=user).first()
            if saved is None:
                # Same message for "not yours" and "does not exist".
                raise serializers.ValidationError({"address_id": "Address not found."})
            attrs["address"] = DeliveryAddressSerializer(saved).data
        attrs["address"] = dict(attrs["address"])
        return attrs
