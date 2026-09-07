"""Tests for bespoke measurement validation.

The failure this guards against is concrete: a mis-keyed measurement is not
caught until a tailor has cut into fabric for a garment that may be worth tens
of thousands of rupees. Unit confusion (entering centimetres while 'inch' is
selected) is the most common real-world cause.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.tailoring.validators import (  # noqa: E402
    MEASUREMENT_RANGES,
    REQUIRED_BY_GARMENT,
    MeasurementError,
    validate_measurements,
    validate_preferences,
)

pytestmark = pytest.mark.unit

VALID_SUIT = {
    "bust": 36,
    "waist": 30,
    "hip": 38,
    "shoulder": 14,
    "kameez_length": 42,
    "sleeve_length": 22,
}


class TestHappyPath:
    def test_valid_inch_measurements_accepted(self):
        result = validate_measurements(VALID_SUIT, unit_system="inch", garment_type="suit_set")
        assert result["bust"] == 36.0

    def test_valid_cm_measurements_accepted(self):
        cm = {k: round(v * 2.54, 1) for k, v in VALID_SUIT.items()}
        result = validate_measurements(cm, unit_system="cm", garment_type="suit_set")
        assert result["bust"] == pytest.approx(91.4, abs=0.1)

    def test_garment_type_optional(self):
        assert validate_measurements({"bust": 36}, unit_system="inch")

    def test_decimal_strings_accepted(self):
        result = validate_measurements({"bust": "36.5"}, unit_system="inch")
        assert result["bust"] == 36.5

    def test_farshi_palazzo_flare(self):
        payload = {"waist": 30, "hip": 38, "trouser_length": 40, "farshi_flare": 120}
        assert validate_measurements(payload, unit_system="inch", garment_type="farshi_palazzo")


class TestUnitConfusion:
    """The highest-value class in this file."""

    def test_cm_value_entered_as_inches_is_rejected(self):
        """91 cm bust entered while 'inch' is selected: 91in = 231cm."""
        with pytest.raises(MeasurementError, match="Bust"):
            validate_measurements({"bust": 91}, unit_system="inch")

    def test_inch_value_entered_as_cm_is_rejected(self):
        """36 entered as cm is a 14-inch bust - implausible."""
        with pytest.raises(MeasurementError, match="Bust"):
            validate_measurements({"bust": 36}, unit_system="cm")

    def test_error_names_both_value_and_unit(self):
        """The message must help the customer self-correct."""
        with pytest.raises(MeasurementError) as exc:
            validate_measurements({"bust": 400}, unit_system="inch")
        message = str(exc.value)
        assert "400" in message
        assert "inch" in message
        assert "unit" in message.lower()


class TestRangeValidation:
    def test_absurdly_large_rejected(self):
        with pytest.raises(MeasurementError, match="outside the plausible range"):
            validate_measurements({"bust": 400}, unit_system="inch")

    def test_zero_rejected(self):
        with pytest.raises(MeasurementError, match="greater than zero"):
            validate_measurements({"bust": 0}, unit_system="inch")

    def test_negative_rejected(self):
        with pytest.raises(MeasurementError, match="greater than zero"):
            validate_measurements({"bust": -36}, unit_system="inch")

    def test_boundary_values_accepted(self):
        spec = MEASUREMENT_RANGES["bust"]
        assert validate_measurements({"bust": float(spec.min_in)}, unit_system="inch")
        assert validate_measurements({"bust": float(spec.max_in)}, unit_system="inch")

    def test_just_outside_boundary_rejected(self):
        spec = MEASUREMENT_RANGES["bust"]
        with pytest.raises(MeasurementError):
            validate_measurements({"bust": float(spec.max_in) + 1}, unit_system="inch")

    def test_generous_ranges_do_not_police_body_size(self):
        """A genuinely large but real measurement must be accepted."""
        assert validate_measurements({"bust": 62, "waist": 58, "hip": 70}, unit_system="inch")


class TestCoherence:
    def test_underbust_exceeding_bust_rejected(self):
        with pytest.raises(MeasurementError, match="Underbust cannot exceed bust"):
            validate_measurements({"bust": 34, "underbust": 40}, unit_system="inch")

    def test_wrist_exceeding_bicep_rejected(self):
        # Both values sit inside their own ranges; only the pairing is wrong.
        with pytest.raises(MeasurementError, match="Wrist cannot exceed bicep"):
            validate_measurements({"bicep": 8, "wrist": 13}, unit_system="inch")

    def test_knee_exceeding_thigh_rejected(self):
        with pytest.raises(MeasurementError, match="Knee cannot exceed thigh"):
            validate_measurements({"thigh": 20, "knee": 25}, unit_system="inch")

    def test_implausible_waist_to_bust_rejected(self):
        with pytest.raises(MeasurementError, match="Waist is implausibly large"):
            validate_measurements({"bust": 30, "waist": 60}, unit_system="inch")

    def test_ghera_narrower_than_flare_rejected(self):
        with pytest.raises(MeasurementError, match="Ghera"):
            validate_measurements(
                {"farshi_flare": 120, "ghera": 80}, unit_system="inch"
            )

    def test_transposed_digits_caught_by_coherence(self):
        """A 36 bust keyed as 63 with a 30 waist is individually plausible."""
        assert validate_measurements({"bust": 63, "waist": 30}, unit_system="inch")
        # but the reverse transposition trips the coherence rule
        with pytest.raises(MeasurementError):
            validate_measurements({"bust": 30, "waist": 63}, unit_system="inch")

    def test_valid_hourglass_accepted(self):
        assert validate_measurements(
            {"bust": 38, "underbust": 32, "waist": 28, "hip": 40}, unit_system="inch"
        )


class TestRequiredFields:
    def test_missing_required_measurement_rejected(self):
        with pytest.raises(MeasurementError, match="Missing measurements"):
            validate_measurements({"bust": 36}, unit_system="inch", garment_type="suit_set")

    def test_error_lists_missing_labels(self):
        with pytest.raises(MeasurementError) as exc:
            validate_measurements({"bust": 36}, unit_system="inch", garment_type="suit_set")
        assert "Waist" in str(exc.value)
        assert "Kameez length" in str(exc.value)

    def test_farshi_palazzo_requires_flare(self):
        with pytest.raises(MeasurementError, match="Farshi flare"):
            validate_measurements(
                {"waist": 30, "hip": 38, "trouser_length": 40},
                unit_system="inch",
                garment_type="farshi_palazzo",
            )

    def test_dress_material_requires_nothing(self):
        assert validate_measurements({}, unit_system="inch", garment_type="dress_material") == {}

    def test_unknown_garment_type_rejected(self):
        with pytest.raises(MeasurementError, match="Unknown garment type"):
            validate_measurements({}, unit_system="inch", garment_type="spacesuit")

    def test_every_required_key_has_a_range(self):
        """A garment cannot require a measurement the validator cannot check."""
        for garment, keys in REQUIRED_BY_GARMENT.items():
            for key in keys:
                assert key in MEASUREMENT_RANGES, f"{garment} requires unknown key {key}"


class TestInputHygiene:
    def test_unknown_key_rejected(self):
        with pytest.raises(MeasurementError, match="Unsupported measurement keys"):
            validate_measurements({"inseam_of_doom": 30}, unit_system="inch")

    def test_non_dict_rejected(self):
        with pytest.raises(MeasurementError, match="must be a JSON object"):
            validate_measurements([36, 30], unit_system="inch")

    def test_non_numeric_rejected(self):
        with pytest.raises(MeasurementError, match="not a valid number"):
            validate_measurements({"bust": "thirty-six"}, unit_system="inch")

    def test_boolean_rejected(self):
        """True would otherwise coerce to 1 and silently pass as a measurement."""
        with pytest.raises(MeasurementError, match="expected a number"):
            validate_measurements({"bust": True}, unit_system="inch")

    def test_nan_rejected(self):
        with pytest.raises(MeasurementError, match="finite"):
            validate_measurements({"bust": float("nan")}, unit_system="inch")

    def test_infinity_rejected(self):
        with pytest.raises(MeasurementError, match="finite"):
            validate_measurements({"bust": float("inf")}, unit_system="inch")

    def test_bad_unit_system_rejected(self):
        with pytest.raises(MeasurementError, match="unit_system"):
            validate_measurements({"bust": 36}, unit_system="cubits")


class TestPreferences:
    def test_valid_preferences_accepted(self):
        result = validate_preferences(
            {"sleeve_type": "full", "lining_preference": "full", "neckline_style": "round"}
        )
        assert result["sleeve_type"] == "full"

    def test_empty_accepted(self):
        assert validate_preferences({}) == {}

    def test_unknown_key_rejected(self):
        with pytest.raises(MeasurementError, match="Unsupported preference keys"):
            validate_preferences({"vibe": "regal"})

    def test_invalid_value_rejected(self):
        with pytest.raises(MeasurementError, match="not a recognised option"):
            validate_preferences({"lining_preference": "maybe"})

    def test_error_lists_valid_options(self):
        with pytest.raises(MeasurementError) as exc:
            validate_preferences({"sleeve_type": "wizard"})
        assert "full" in str(exc.value)

    def test_non_string_value_rejected(self):
        with pytest.raises(MeasurementError, match="expected a string"):
            validate_preferences({"sleeve_type": 3})

    def test_non_dict_rejected(self):
        with pytest.raises(MeasurementError, match="must be a JSON object"):
            validate_preferences("full")
