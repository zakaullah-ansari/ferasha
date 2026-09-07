"""Controlled vocabularies for the Ferasha catalogue.

Every enum here is mirrored by a database CheckConstraint. Application-level
choice validation is a usability feature; the constraint is the guarantee.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProductStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PENDING_REVIEW = "pending_review", _("Pending review")
    ACTIVE = "active", _("Active")
    OUT_OF_STOCK = "out_of_stock", _("Out of stock")
    ARCHIVED = "archived", _("Archived")


class GarmentType(models.TextChoices):
    """Drives which measurements the Phase 1 fit validator requires."""

    SUIT_SET = "suit_set", _("Suit / Kameez set")
    DRESS_MATERIAL = "dress_material", _("Unstitched dress material")
    LEHENGA = "lehenga", _("Lehenga")
    SHARARA = "sharara", _("Sharara")
    GHARARA = "gharara", _("Gharara")
    FARSHI_PALAZZO = "farshi_palazzo", _("Farshi palazzo")
    FARSHI_SALWAR = "farshi_salwar", _("Farshi salwar")
    PALAZZO = "palazzo", _("Palazzo / Pants")
    GOWN = "gown", _("Gown")
    TAIL_GOWN = "tail_gown", _("Tail gown")
    BLOUSE = "blouse", _("Blouse")
    JACKET = "jacket", _("Jacket")
    LONG_JACKET = "long_jacket", _("Long jacket")
    DUPATTA = "dupatta", _("Dupatta / Stole")


class Fabric(models.TextChoices):
    LAWN = "lawn", _("Lawn")
    CHIFFON = "chiffon", _("Chiffon")
    ORGANZA = "organza", _("Organza")
    GEORGETTE = "georgette", _("Georgette")
    VELVET = "velvet", _("Velvet")
    SILK = "silk", _("Silk")
    RAW_SILK = "raw_silk", _("Raw silk")
    BANARASI = "banarasi", _("Banarasi")
    COTTON = "cotton", _("Cotton")
    LINEN = "linen", _("Linen")
    NET = "net", _("Net")
    TISSUE = "tissue", _("Tissue")
    CREPE = "crepe", _("Crepe")
    JACQUARD = "jacquard", _("Jacquard")


class WorkType(models.TextChoices):
    PLAIN = "plain", _("Plain / Unembellished")
    ZARDOZI = "zardozi", _("Zardozi")
    GOTA_PATTI = "gota_patti", _("Gota patti")
    MIRROR = "mirror", _("Mirror / Sheesha")
    CHIKANKARI = "chikankari", _("Chikankari")
    MUKAISH = "mukaish", _("Mukaish")
    RESHAM = "resham", _("Resham thread")
    SEQUIN = "sequin", _("Sequin")
    DABKA = "dabka", _("Dabka")
    PRINTED = "printed", _("Printed")
    BLOCK_PRINT = "block_print", _("Block print")


class Occasion(models.TextChoices):
    BRIDAL = "bridal", _("Bridal")
    MEHNDI = "mehndi", _("Mehndi")
    NIKAH = "nikah", _("Nikah")
    WALIMA = "walima", _("Walima")
    EID = "eid", _("Eid")
    PARTY = "party", _("Party")
    FORMAL = "formal", _("Formal")
    CASUAL = "casual", _("Casual / Daily")


# --- Modesty vocabularies ---------------------------------------------------
# Ordered from least to most covering. Ordering is load-bearing: the badge
# derivation compares positions, so DO NOT reorder without updating
# apps/catalog/modesty.py and its truth-table tests.


class SlitCoverage(models.TextChoices):
    NONE = "none", _("No slit")
    ANKLE = "ankle", _("Ankle-height slit")
    MID_CALF = "mid_calf", _("Mid-calf slit")
    KNEE = "knee", _("Knee-height slit")
    THIGH = "thigh", _("Thigh-height slit")


class SleeveCoverage(models.TextChoices):
    SLEEVELESS = "sleeveless", _("Sleeveless")
    CAP = "cap", _("Cap sleeve")
    SHORT = "short", _("Short sleeve")
    ELBOW = "elbow", _("Elbow length")
    THREE_QUARTER = "three_quarter", _("Three-quarter")
    FULL = "full", _("Full length")
    EXTRA_LONG = "extra_long", _("Extra long")


class NecklineModesty(models.TextChoices):
    DEEP = "deep", _("Deep")
    MODERATE = "moderate", _("Moderate")
    HIGH = "high", _("High")
    CLOSED = "closed", _("Closed / Collared")


class BackCoverage(models.TextChoices):
    OPEN = "open", _("Open back")
    DEEP = "deep", _("Deep back")
    MODERATE = "moderate", _("Moderate")
    FULL = "full", _("Fully covered")


#: Coverage rankings, least to most covering.
SLIT_ORDER = (
    SlitCoverage.THIGH,
    SlitCoverage.KNEE,
    SlitCoverage.MID_CALF,
    SlitCoverage.ANKLE,
    SlitCoverage.NONE,
)
SLEEVE_ORDER = (
    SleeveCoverage.SLEEVELESS,
    SleeveCoverage.CAP,
    SleeveCoverage.SHORT,
    SleeveCoverage.ELBOW,
    SleeveCoverage.THREE_QUARTER,
    SleeveCoverage.FULL,
    SleeveCoverage.EXTRA_LONG,
)
NECKLINE_ORDER = (
    NecklineModesty.DEEP,
    NecklineModesty.MODERATE,
    NecklineModesty.HIGH,
    NecklineModesty.CLOSED,
)
BACK_ORDER = (
    BackCoverage.OPEN,
    BackCoverage.DEEP,
    BackCoverage.MODERATE,
    BackCoverage.FULL,
)


def coverage_rank(value: str, order: tuple) -> int:
    """Position of ``value`` in a coverage ordering. Higher is more covering."""
    try:
        return order.index(value)
    except ValueError as exc:
        raise ValueError(f"{value!r} is not a member of the given coverage ordering.") from exc


class SizeStandard(models.TextChoices):
    XS = "XS", _("XS")
    S = "S", _("S")
    M = "M", _("M")
    L = "L", _("L")
    XL = "XL", _("XL")
    XXL = "XXL", _("XXL")
    XXXL = "XXXL", _("XXXL")
    FREE = "FREE", _("Free size")
    CUSTOM = "CUSTOM", _("Made to measure")


class UnitSystem(models.TextChoices):
    CM = "cm", _("Centimetres")
    INCH = "inch", _("Inches")
