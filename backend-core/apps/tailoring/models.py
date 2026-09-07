"""Bespoke tailoring: fit profiles, their revision history and order specs.

Measurements are stored in ``models.JSONField``, which maps to native ``jsonb``
on PostgreSQL. (``models.JSONBField`` does not exist in Django 5; JSONField is
the correct API and gives the same storage type.)

The shape is genuinely variable - a farshi palazzo needs ``farshi_flare`` and a
blouse does not - which is why this is jsonb, unlike the fixed modesty
attributes in apps.catalog which are typed columns.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalog.enums import GarmentType, UnitSystem
from apps.common.models import BaseModel

from .validators import MeasurementError, validate_measurements, validate_preferences


class MeasuredBy(models.TextChoices):
    SELF = "self", _("Measured by customer")
    TAILOR = "tailor", _("Measured by Ferasha tailor")
    STYLIST = "stylist", _("Measured by stylist")
    EXISTING_GARMENT = "existing_garment", _("Copied from an existing garment")


class BespokeFitProfile(BaseModel):
    """A customer's saved measurement set.

    A customer may hold several - "my measurements", "sister's measurements" -
    so the profile is named rather than being a singleton per user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fit_profiles"
    )
    label = models.CharField(max_length=80, help_text=_("e.g. 'My measurements'"))

    #: Native jsonb. Validated on save by apps.tailoring.validators.
    measurements = models.JSONField(default=dict)
    preferences = models.JSONField(default=dict, blank=True)

    unit_system = models.CharField(
        max_length=4, choices=UnitSystem.choices, default=UnitSystem.INCH
    )
    #: Optional: when set, required-field validation for that garment applies.
    garment_type = models.CharField(
        max_length=24, choices=GarmentType.choices, blank=True
    )
    measured_by = models.CharField(
        max_length=18, choices=MeasuredBy.choices, default=MeasuredBy.SELF
    )
    notes = models.TextField(blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_fit_profiles",
        limit_choices_to={"role__in": ["tailor", "stylist", "staff", "admin"]},
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_default", "-updated_at")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "label"], name="unique_fit_profile_label_per_user"
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_fit_profile_per_user",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_system__in=[c[0] for c in UnitSystem.choices]),
                name="fit_profile_unit_system_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="fitprofile_user_recent_idx"),
            # GIN over the jsonb so containment queries on measurements are
            # indexed rather than sequential scans.
            GinIndex(fields=["measurements"], name="fitprofile_measurements_gin"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.user.email})"

    def clean(self):
        super().clean()
        try:
            self.measurements = validate_measurements(
                self.measurements,
                unit_system=self.unit_system,
                garment_type=self.garment_type or None,
            )
            self.preferences = validate_preferences(self.preferences or {})
        except MeasurementError as exc:
            raise ValidationError({"measurements": str(exc)}) from exc

    def save(self, *args, **kwargs):
        # Validation runs on every save, including from the admin and shell.
        # A jsonb column is only as trustworthy as its narrowest write path.
        self.full_clean(exclude=["verified_by", "user"])
        super().save(*args, **kwargs)

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

    def snapshot(self) -> dict:
        """Immutable copy for attaching to an order."""
        return {
            "profile_id": str(self.id),
            "label": self.label,
            "measurements": dict(self.measurements),
            "preferences": dict(self.preferences),
            "unit_system": self.unit_system,
            "measured_by": self.measured_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "captured_at": timezone.now().isoformat(),
        }


class FitProfileRevision(models.Model):
    """Append-only history of a fit profile.

    Measurements change between orders. When a customer disputes a garment
    ("you stitched it wrong"), the only defensible answer comes from knowing
    exactly what was specified at the time. This table is never updated and
    never deleted.
    """

    id = models.BigAutoField(primary_key=True)
    profile = models.ForeignKey(
        BespokeFitProfile, on_delete=models.CASCADE, related_name="revisions"
    )
    revision = models.PositiveIntegerField()
    measurements = models.JSONField()
    preferences = models.JSONField(default=dict)
    unit_system = models.CharField(max_length=4)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    change_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-revision",)
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "revision"], name="unique_revision_per_profile"
            ),
        ]
        indexes = [
            models.Index(fields=["profile", "-revision"], name="revision_profile_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} r{self.revision}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(
                "FitProfileRevision is append-only; an existing revision cannot be modified."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("FitProfileRevision is append-only; revisions cannot be deleted.")


class TailoringOrderSpec(BaseModel):
    """The frozen measurement set an order is actually cut from.

    Deliberately a snapshot, never a live FK to BespokeFitProfile. The profile
    mutates; what the atelier cut must not.
    """

    order_line = models.OneToOneField(
        "orders.OrderLine", on_delete=models.CASCADE, related_name="tailoring_spec"
    )
    source_profile = models.ForeignKey(
        BespokeFitProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_specs",
        help_text=_("Provenance only. The authoritative values are in this row."),
    )

    measurements = models.JSONField()
    preferences = models.JSONField(default=dict)
    unit_system = models.CharField(max_length=4, choices=UnitSystem.choices)
    garment_type = models.CharField(max_length=24, choices=GarmentType.choices)

    special_instructions = models.TextField(blank=True)
    surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    measurement_reviewed_at = models.DateTimeField(null=True, blank=True)
    measurement_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_specs",
    )
    review_notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(surcharge__gte=Decimal("0.00")),
                name="spec_surcharge_non_negative",
            ),
        ]
        indexes = [
            GinIndex(fields=["measurements"], name="spec_measurements_gin"),
        ]

    def __str__(self) -> str:
        return f"Spec for line {self.order_line_id}"

    @property
    def is_reviewed(self) -> bool:
        return self.measurement_reviewed_at is not None
