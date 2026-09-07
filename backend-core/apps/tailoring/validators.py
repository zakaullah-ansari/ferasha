"""Validation for bespoke measurement JSON.

A jsonb column with no schema is a data-integrity hole. Wrong measurements mean
a ruined bridal lehenga, a refund, and a customer lost permanently - the most
expensive failure mode in the business. Every write is therefore validated for
presence, type, plausibility and cross-field coherence.

Pure Python with no Django model imports so it is unit-testable in isolation
and reusable by the ai-engine's measurement assistant (Phase 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CM_PER_INCH = Decimal("2.54")


class MeasurementError(ValueError):
    """Raised when a measurement set cannot be trusted to cut cloth from."""


@dataclass(frozen=True, slots=True)
class Range:
    """Plausible range for one measurement, expressed in inches."""

    min_in: Decimal
    max_in: Decimal
    label: str

    def contains(self, inches: Decimal) -> bool:
        return self.min_in <= inches <= self.max_in


#: Plausibility ranges in INCHES, deliberately generous at both ends - the
#: purpose is to catch unit confusion and typos (a "bust" of 400), not to
#: police body size. Rejecting a real customer's real measurement would be a
#: far worse failure than accepting an unusual one.
MEASUREMENT_RANGES: dict[str, Range] = {
    "bust": Range(Decimal("24"), Decimal("70"), "Bust"),
    "underbust": Range(Decimal("22"), Decimal("66"), "Underbust"),
    "waist": Range(Decimal("18"), Decimal("70"), "Waist"),
    "hip": Range(Decimal("24"), Decimal("80"), "Hip"),
    "shoulder": Range(Decimal("10"), Decimal("26"), "Shoulder"),
    "kameez_length": Range(Decimal("20"), Decimal("60"), "Kameez length"),
    "sleeve_length": Range(Decimal("0"), Decimal("30"), "Sleeve length"),
    "armhole": Range(Decimal("10"), Decimal("28"), "Armhole"),
    "bicep": Range(Decimal("7"), Decimal("28"), "Bicep"),
    "wrist": Range(Decimal("4"), Decimal("14"), "Wrist"),
    "neck_depth_front": Range(Decimal("2"), Decimal("20"), "Front neck depth"),
    "neck_depth_back": Range(Decimal("2"), Decimal("20"), "Back neck depth"),
    "trouser_length": Range(Decimal("20"), Decimal("50"), "Trouser length"),
    "thigh": Range(Decimal("12"), Decimal("45"), "Thigh"),
    "knee": Range(Decimal("10"), Decimal("32"), "Knee"),
    "ankle_opening": Range(Decimal("6"), Decimal("30"), "Ankle opening"),
    "farshi_flare": Range(Decimal("40"), Decimal("200"), "Farshi flare"),
    "ghera": Range(Decimal("40"), Decimal("240"), "Ghera (hem sweep)"),
    "lehenga_length": Range(Decimal("30"), Decimal("55"), "Lehenga length"),
    "blouse_length": Range(Decimal("10"), Decimal("30"), "Blouse length"),
    "dupatta_length": Range(Decimal("60"), Decimal("120"), "Dupatta length"),
}

#: Required measurements per garment type. Cutting cloth without these is
#: guesswork.
REQUIRED_BY_GARMENT: dict[str, tuple[str, ...]] = {
    "suit_set": ("bust", "waist", "hip", "shoulder", "kameez_length", "sleeve_length"),
    "lehenga": ("bust", "waist", "hip", "lehenga_length", "blouse_length"),
    "sharara": ("bust", "waist", "hip", "kameez_length", "trouser_length"),
    "gharara": ("bust", "waist", "hip", "kameez_length", "trouser_length"),
    "farshi_palazzo": ("waist", "hip", "trouser_length", "farshi_flare"),
    "farshi_salwar": ("waist", "hip", "trouser_length", "farshi_flare"),
    "palazzo": ("waist", "hip", "trouser_length"),
    "gown": ("bust", "waist", "hip", "shoulder", "kameez_length", "sleeve_length"),
    "tail_gown": ("bust", "waist", "hip", "shoulder", "kameez_length", "sleeve_length"),
    "blouse": ("bust", "underbust", "shoulder", "blouse_length", "sleeve_length", "armhole"),
    "jacket": ("bust", "waist", "shoulder", "sleeve_length"),
    "long_jacket": ("bust", "waist", "hip", "shoulder", "sleeve_length", "kameez_length"),
    "dress_material": (),
    "dupatta": (),
}

VALID_SLEEVE_TYPES = frozenset(
    {"sleeveless", "cap", "short", "elbow", "three_quarter", "full", "bell",
     "bishop", "kimono", "raglan", "puff"}
)
VALID_LINING = frozenset({"none", "partial", "full", "full_with_canvas"})
VALID_NECKLINE = frozenset(
    {"round", "v_neck", "boat", "square", "sweetheart", "collar", "keyhole", "high_neck"}
)
VALID_CLOSURE = frozenset({"zip_back", "zip_side", "button_front", "hook_back", "tie_back", "none"})
VALID_HEM = frozenset({"plain", "piped", "lace", "scalloped", "raw", "rolled"})

PREFERENCE_VOCABULARIES: dict[str, frozenset[str]] = {
    "sleeve_type": VALID_SLEEVE_TYPES,
    "lining_preference": VALID_LINING,
    "neckline_style": VALID_NECKLINE,
    "closure_type": VALID_CLOSURE,
    "hem_finish": VALID_HEM,
}


def _to_inches(value: Decimal, unit_system: str) -> Decimal:
    return value if unit_system == "inch" else value / CM_PER_INCH


def _coerce(name: str, raw: object) -> Decimal:
    if isinstance(raw, bool):
        raise MeasurementError(f"{name}: expected a number, got a boolean.")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MeasurementError(f"{name}: {raw!r} is not a valid number.") from exc
    if not value.is_finite():
        raise MeasurementError(f"{name}: value must be finite.")
    return value


def validate_measurements(
    measurements: object,
    *,
    unit_system: str,
    garment_type: str | None = None,
) -> dict[str, float]:
    """Validate a measurement payload. Returns the normalised dict.

    Raises ``MeasurementError`` with a message safe to show a customer.
    """
    if not isinstance(measurements, dict):
        raise MeasurementError("Measurements must be a JSON object.")
    if unit_system not in {"cm", "inch"}:
        raise MeasurementError("unit_system must be 'cm' or 'inch'.")

    unknown = set(measurements) - set(MEASUREMENT_RANGES)
    if unknown:
        raise MeasurementError(
            "Unsupported measurement keys: " + ", ".join(sorted(unknown))
        )

    normalised: dict[str, float] = {}
    inches: dict[str, Decimal] = {}

    for name, raw in measurements.items():
        value = _coerce(name, raw)
        if value <= 0:
            raise MeasurementError(f"{MEASUREMENT_RANGES[name].label} must be greater than zero.")
        as_inches = _to_inches(value, unit_system)
        spec = MEASUREMENT_RANGES[name]
        if not spec.contains(as_inches):
            lo, hi = (
                (spec.min_in, spec.max_in)
                if unit_system == "inch"
                else (spec.min_in * CM_PER_INCH, spec.max_in * CM_PER_INCH)
            )
            raise MeasurementError(
                f"{spec.label} of {value} {unit_system} is outside the plausible range "
                f"({lo:.0f}-{hi:.0f} {unit_system}). Please check the value and the "
                f"unit you selected."
            )
        inches[name] = as_inches
        normalised[name] = float(value)

    if garment_type is not None:
        required = REQUIRED_BY_GARMENT.get(garment_type)
        if required is None:
            raise MeasurementError(f"Unknown garment type {garment_type!r}.")
        missing = [MEASUREMENT_RANGES[k].label for k in required if k not in measurements]
        if missing:
            raise MeasurementError(
                "Missing measurements required for this garment: " + ", ".join(missing)
            )

    _validate_coherence(inches)
    return normalised


def _validate_coherence(inches: dict[str, Decimal]) -> None:
    """Cross-field checks.

    Each individual value can be plausible while the combination is not - a
    common signature of transposed digits or a mis-keyed field.
    """
    bust = inches.get("bust")
    underbust = inches.get("underbust")
    waist = inches.get("waist")
    hip = inches.get("hip")

    if bust is not None and underbust is not None and underbust > bust:
        raise MeasurementError("Underbust cannot exceed bust. Please re-check both values.")

    if bust is not None and waist is not None and waist > bust + Decimal("24"):
        raise MeasurementError(
            "Waist is implausibly large relative to bust. Please re-check both values."
        )

    if hip is not None and waist is not None and waist > hip + Decimal("24"):
        raise MeasurementError(
            "Waist is implausibly large relative to hip. Please re-check both values."
        )

    wrist = inches.get("wrist")
    bicep = inches.get("bicep")
    if wrist is not None and bicep is not None and wrist > bicep:
        raise MeasurementError("Wrist cannot exceed bicep. Please re-check both values.")

    knee = inches.get("knee")
    thigh = inches.get("thigh")
    if knee is not None and thigh is not None and knee > thigh:
        raise MeasurementError("Knee cannot exceed thigh. Please re-check both values.")

    kameez = inches.get("kameez_length")
    trouser = inches.get("trouser_length")
    if kameez is not None and trouser is not None and kameez > trouser + Decimal("18"):
        raise MeasurementError(
            "Kameez length is implausibly long relative to trouser length."
        )

    ghera = inches.get("ghera")
    flare = inches.get("farshi_flare")
    if ghera is not None and flare is not None and ghera < flare:
        raise MeasurementError(
            "Ghera (hem sweep) cannot be narrower than the farshi flare."
        )


def validate_preferences(preferences: object) -> dict[str, str]:
    """Validate the stitching preference payload against fixed vocabularies."""
    if not isinstance(preferences, dict):
        raise MeasurementError("Preferences must be a JSON object.")

    unknown = set(preferences) - set(PREFERENCE_VOCABULARIES)
    if unknown:
        raise MeasurementError(
            "Unsupported preference keys: " + ", ".join(sorted(unknown))
        )

    cleaned: dict[str, str] = {}
    for key, value in preferences.items():
        if not isinstance(value, str):
            raise MeasurementError(f"{key}: expected a string value.")
        vocabulary = PREFERENCE_VOCABULARIES[key]
        if value not in vocabulary:
            raise MeasurementError(
                f"{key}: {value!r} is not a recognised option "
                f"({', '.join(sorted(vocabulary))})."
            )
        cleaned[key] = value
    return cleaned
