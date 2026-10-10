"""Static GST reference data for the Ferasha tax engine.

Kept free of Django imports so the calculator remains a pure-Python module that
can be unit tested, or reused by the ai-engine, without booting the ORM.

RATE HISTORY
------------
The 56th GST Council meeting ("GST 2.0") restructured apparel taxation with
effect from **22 September 2025**:

* the concessional 5% threshold rose from Rs.1,000 to Rs.2,500 per piece;
* the upper apparel slab moved from 12% to 18%;
* the 12% slab was abolished for textiles entirely.

Ferasha must be able to reproduce the tax on an invoice raised at any point in
its trading history, so rates are stored as date-effective regimes rather than
as bare constants. ``resolve_regime(as_of)`` selects the correct one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal
from types import MappingProxyType

# ISO 3166-2:IN subdivision code -> GST state numeric code.
INDIAN_STATE_GST_CODES: MappingProxyType[str, str] = MappingProxyType(
    {
        "JK": "01", "HP": "02", "PB": "03", "CH": "04", "UT": "05", "UK": "05",
        "HR": "06", "DL": "07", "RJ": "08", "UP": "09", "BR": "10", "SK": "11",
        "AR": "12", "NL": "13", "MN": "14", "MZ": "15", "TR": "16", "ML": "17",
        "AS": "18", "WB": "19", "JH": "20", "OR": "21", "OD": "21", "CT": "22",
        "CG": "22", "MP": "23", "GJ": "24", "DH": "26", "DN": "26", "DD": "26",
        "MH": "27", "KA": "29", "GA": "30", "LD": "31", "KL": "32", "TN": "33",
        "PY": "34", "AN": "35", "TG": "36", "TS": "36", "AP": "37", "LA": "38",
        "OT": "97",
    }
)

# --- HSN / SAC codes Ferasha transacts in -----------------------------------
HSN_KNITTED_APPAREL = "6104"       # Knitted/crocheted women's suits, ensembles
HSN_WOMENS_SUITS = "6204"          # Non-knitted suits, ensembles, kameez sets
HSN_SAREES_LEHENGA = "6211"        # Other garments incl. lehenga, gharara
HSN_DUPATTA_STOLE = "6214"         # Dupattas, shawls, scarves, stoles
HSN_BLOUSE_JACKET = "6206"         # Blouses, shirts, shirt-blouses
HSN_MADE_UP_TEXTILE = "6307"       # Other made-up textile articles, sets
HSN_FABRIC_WOVEN_COTTON = "5208"   # Unstitched dress material / fabric
HSN_FABRIC_SYNTHETIC = "5407"      # Woven synthetic filament fabric

SAC_TAILORING_SERVICE = "998821"   # Textile manufacturing services
SAC_ALTERATION_SERVICE = "999722"  # Repair / alteration of apparel
SAC_COURIER_SERVICE = "996812"     # Courier / delivery services

# Garments taxed on the per-piece value slab.
VALUE_SLABBED_HSN = frozenset(
    {
        HSN_KNITTED_APPAREL,
        HSN_WOMENS_SUITS,
        HSN_SAREES_LEHENGA,
        HSN_DUPATTA_STOLE,
        HSN_BLOUSE_JACKET,
        HSN_MADE_UP_TEXTILE,
    }
)

# Unstitched fabric / dress material is a flat 5% regardless of value.
FABRIC_HSN = frozenset({HSN_FABRIC_WOVEN_COTTON, HSN_FABRIC_SYNTHETIC})

ZERO_RATE = Decimal("0")


@dataclass(frozen=True, slots=True)
class GSTRegime:
    """A date-effective set of GST rates.

    ``effective_from`` is inclusive. Regimes must be registered in ascending
    date order in ``GST_REGIMES``.
    """

    name: str
    effective_from: date
    apparel_threshold: Decimal
    apparel_rate_at_or_below: Decimal
    apparel_rate_above: Decimal
    fabric_rate: Decimal
    tailoring_service_rate: Decimal
    courier_service_rate: Decimal
    permitted_rates: frozenset[Decimal]

    def flat_rate_codes(self) -> dict[str, Decimal]:
        """HSN/SAC codes carrying a flat rate regardless of value."""
        return {
            SAC_TAILORING_SERVICE: self.tailoring_service_rate,
            SAC_ALTERATION_SERVICE: self.tailoring_service_rate,
            SAC_COURIER_SERVICE: self.courier_service_rate,
            HSN_FABRIC_WOVEN_COTTON: self.fabric_rate,
            HSN_FABRIC_SYNTHETIC: self.fabric_rate,
        }


# Pre-GST-2.0 regime. Retained so invoices raised before 22 Sep 2025 can be
# reproduced exactly during an audit or a return/credit-note against an old order.
REGIME_2017 = GSTRegime(
    name="GST 1.0 (pre-rationalisation)",
    effective_from=date(2017, 7, 1),
    apparel_threshold=Decimal("1000.00"),
    apparel_rate_at_or_below=Decimal("5"),
    apparel_rate_above=Decimal("12"),
    fabric_rate=Decimal("5"),
    tailoring_service_rate=Decimal("5"),
    courier_service_rate=Decimal("18"),
    permitted_rates=frozenset({Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")}),
)

# GST 2.0, 56th GST Council, effective 22 September 2025.
# Threshold Rs.1,000 -> Rs.2,500; upper apparel slab 12% -> 18%; 12% abolished.
REGIME_2025 = GSTRegime(
    name="GST 2.0 (56th Council, w.e.f. 22 Sep 2025)",
    effective_from=date(2025, 9, 22),
    apparel_threshold=Decimal("2500.00"),
    apparel_rate_at_or_below=Decimal("5"),
    apparel_rate_above=Decimal("18"),
    fabric_rate=Decimal("5"),
    tailoring_service_rate=Decimal("5"),
    courier_service_rate=Decimal("18"),
    # 12% is deliberately absent: the slab no longer exists for our catalogue.
    permitted_rates=frozenset({Decimal("0"), Decimal("5"), Decimal("18"), Decimal("40")}),
)

GST_REGIMES: tuple[GSTRegime, ...] = (REGIME_2017, REGIME_2025)

CURRENT_REGIME = GST_REGIMES[-1]


def resolve_regime(as_of: date | None = None) -> GSTRegime:
    """Return the GST regime in force on ``as_of`` (default: today)."""
    if as_of is None:
        from datetime import datetime

        as_of = datetime.now(UTC).date()
    applicable = [r for r in GST_REGIMES if r.effective_from <= as_of]
    if not applicable:
        raise ValueError(
            f"No GST regime is defined for {as_of.isoformat()}; the earliest is "
            f"{GST_REGIMES[0].effective_from.isoformat()}."
        )
    return applicable[-1]


# --- Backwards-compatible aliases (current regime) ---------------------------
APPAREL_SLAB_THRESHOLD = CURRENT_REGIME.apparel_threshold
APPAREL_RATE_BELOW_THRESHOLD = CURRENT_REGIME.apparel_rate_at_or_below
APPAREL_RATE_ABOVE_THRESHOLD = CURRENT_REGIME.apparel_rate_above
SERVICE_RATE_STANDARD = CURRENT_REGIME.courier_service_rate
TAILORING_SERVICE_RATE = CURRENT_REGIME.tailoring_service_rate
FLAT_RATE_HSN: MappingProxyType[str, Decimal] = MappingProxyType(CURRENT_REGIME.flat_rate_codes())
PERMITTED_GST_RATES = CURRENT_REGIME.permitted_rates
