"""Static GST reference data for the Ferasha tax engine.

Kept free of Django imports so the calculator remains a pure-Python module that
can be unit tested, or reused by the ai-engine, without booting the ORM.
"""

from __future__ import annotations

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

# Harmonised System of Nomenclature codes Ferasha transacts in.
HSN_WOMENS_SUITS = "6204"          # Suits, ensembles, kameez, kurta sets
HSN_SAREES_LEHENGA = "6211"        # Other garments incl. lehenga, gharara
HSN_DUPATTA_STOLE = "6214"         # Dupattas, shawls, stoles
HSN_MADE_UP_TEXTILE = "6307"       # Other made-up textile articles
HSN_TAILORING_SERVICE = "998821"   # SAC: textile manufacturing services
HSN_ALTERATION_SERVICE = "999722"  # SAC: repair/alteration of apparel

# Apparel slab boundary. Garments with a taxable value per piece at or below
# this threshold attract 5%; above it, 12%. Comparison is on the per-piece
# taxable value AFTER discount, per CBIC valuation rules.
APPAREL_SLAB_THRESHOLD = Decimal("1000.00")
APPAREL_RATE_BELOW_THRESHOLD = Decimal("5")
APPAREL_RATE_ABOVE_THRESHOLD = Decimal("12")
SERVICE_RATE_STANDARD = Decimal("18")
ZERO_RATE = Decimal("0")

# HSN/SAC codes that are value-slabbed rather than flat-rated.
VALUE_SLABBED_HSN = frozenset(
    {HSN_WOMENS_SUITS, HSN_SAREES_LEHENGA, HSN_DUPATTA_STOLE, HSN_MADE_UP_TEXTILE}
)

# HSN/SAC codes carrying a flat rate regardless of value.
FLAT_RATE_HSN: MappingProxyType[str, Decimal] = MappingProxyType(
    {
        HSN_TAILORING_SERVICE: SERVICE_RATE_STANDARD,
        HSN_ALTERATION_SERVICE: SERVICE_RATE_STANDARD,
    }
)

# Every rate the engine is permitted to emit. Guards against typo'd overrides.
PERMITTED_GST_RATES = frozenset(
    {Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")}
)
