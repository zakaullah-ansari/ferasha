"""Bespoke lines: one rule for what may be ordered made to measure.

Checked when a line enters the bag and again at checkout, so a line that got
in some other way (an older client, a direct write) still cannot be ordered.
"""

from __future__ import annotations

from apps.catalog.enums import SizeStandard, UnitSystem
from apps.catalog.models import ProductVariant

from .validators import MeasurementError, validate_measurements, validate_preferences


class BespokeError(ValueError):
    """A bespoke line the customer must correct; the message is customer-safe."""


def validate_bespoke_line(
    variant: ProductVariant, measurements: object, preferences: object = None
) -> tuple[dict[str, float], dict[str, str]]:
    """The cleaned measurements (inches) and preferences for a made-to-measure line.

    Only the made-to-measure (CUSTOM) variant of a product the atelier makes
    to measure qualifies; the measurements must be complete and coherent for
    that garment, in inches - the unit the storefront stores them in.
    """
    product = variant.product
    if not product.supports_bespoke:
        raise BespokeError(f"{product.name} is not made to measure.")
    if variant.size != SizeStandard.CUSTOM:
        raise BespokeError(f"Choose the made-to-measure option for {product.name}.")
    try:
        cleaned = validate_measurements(
            measurements, unit_system=UnitSystem.INCH, garment_type=product.garment_type
        )
        chosen = validate_preferences(preferences or {})
    except MeasurementError as exc:
        raise BespokeError(str(exc)) from exc
    return cleaned, chosen
