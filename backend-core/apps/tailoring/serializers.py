"""Bespoke fit profile serializers.

Measurements are sensitive personal data under the DPDP Act 2023. Every
serializer here assumes the queryset has already been scoped to the requesting
user; ownership is never inferred from a client-supplied ``user`` field.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import BespokeFitProfile, FitProfileRevision, TailoringOrderSpec
from .validators import (
    MEASUREMENT_RANGES,
    REQUIRED_BY_GARMENT,
    MeasurementError,
    validate_measurements,
    validate_preferences,
)


class FitProfileSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = BespokeFitProfile
        fields = (
            "id", "label", "measurements", "preferences", "unit_system",
            "garment_type", "measured_by", "notes", "is_default",
            "is_verified", "verified_at", "created_at", "updated_at",
        )
        read_only_fields = ("id", "is_verified", "verified_at", "created_at", "updated_at")
        # ``user`` is deliberately absent: it is taken from the request, never
        # from the payload. Accepting it would allow writing to another
        # customer's profile.

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance
        measurements = attrs.get(
            "measurements", getattr(instance, "measurements", {})
        )
        unit_system = attrs.get("unit_system", getattr(instance, "unit_system", "inch"))
        garment_type = attrs.get("garment_type", getattr(instance, "garment_type", ""))

        try:
            attrs["measurements"] = validate_measurements(
                measurements, unit_system=unit_system, garment_type=garment_type or None
            )
            if "preferences" in attrs:
                attrs["preferences"] = validate_preferences(attrs["preferences"] or {})
        except MeasurementError as exc:
            # The validator's messages are written to be shown to a customer.
            raise serializers.ValidationError({"measurements": str(exc)}) from exc
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        if validated_data.get("is_default"):
            BespokeFitProfile.objects.filter(user=user, is_default=True).update(
                is_default=False
            )
        elif not BespokeFitProfile.objects.filter(user=user).exists():
            validated_data["is_default"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default"):
            BespokeFitProfile.objects.filter(
                user=instance.user, is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)

        # Snapshot the pre-edit state before mutating. Measurements change
        # between orders; a dispute is only answerable with the history.
        if "measurements" in validated_data or "preferences" in validated_data:
            next_revision = (
                FitProfileRevision.objects.filter(profile=instance).count() + 1
            )
            FitProfileRevision.objects.create(
                profile=instance,
                revision=next_revision,
                measurements=dict(instance.measurements),
                preferences=dict(instance.preferences),
                unit_system=instance.unit_system,
                changed_by=self.context["request"].user,
                change_reason=self.context["request"].data.get("change_reason", "")[:200],
            )
        return super().update(instance, validated_data)


class FitProfileRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitProfileRevision
        fields = (
            "id", "revision", "measurements", "preferences",
            "unit_system", "change_reason", "created_at",
        )
        read_only_fields = fields


class TailoringOrderSpecSerializer(serializers.ModelSerializer):
    is_reviewed = serializers.BooleanField(read_only=True)

    class Meta:
        model = TailoringOrderSpec
        fields = (
            "id", "measurements", "preferences", "unit_system", "garment_type",
            "special_instructions", "surcharge", "is_reviewed",
            "measurement_reviewed_at", "review_notes",
        )
        read_only_fields = fields


class MeasurementGuideSerializer(serializers.Serializer):
    """Machine-readable measurement spec for the frontend FitDrawer.

    The Zod schema in the storefront is generated from this, so the plausibility
    ranges enforced client-side are byte-identical to the ones enforced here.
    Divergence would either reject a valid customer or let a bad measurement
    reach a tailor.
    """

    @staticmethod
    def build() -> dict[str, Any]:
        return {
            "unit_systems": ["inch", "cm"],
            "measurements": {
                key: {
                    "label": spec.label,
                    "min_inch": float(spec.min_in),
                    "max_inch": float(spec.max_in),
                    "min_cm": round(float(spec.min_in) * 2.54, 1),
                    "max_cm": round(float(spec.max_in) * 2.54, 1),
                }
                for key, spec in MEASUREMENT_RANGES.items()
            },
            "required_by_garment": {
                garment: list(keys) for garment, keys in REQUIRED_BY_GARMENT.items()
            },
            "coherence_rules": [
                "Underbust cannot exceed bust.",
                "Wrist cannot exceed bicep.",
                "Knee cannot exceed thigh.",
                "Waist must be within 24 inches of bust and hip.",
                "Ghera cannot be narrower than the farshi flare.",
            ],
        }
