"""Modesty badge derivation.

A **pure function** over a garment's modesty attributes. This module is the
single source of truth for how badges are computed; it is exported to the
frontend through the OpenAPI schema so the storefront never reimplements the
rules in TypeScript. Two implementations would drift, and a garment shown as
"fully covered" that is not is a trust failure, not a cosmetic bug.

No Django model imports here - the function takes plain values so it can be
unit tested against a truth table without touching the ORM.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .enums import (
    BACK_ORDER,
    NECKLINE_ORDER,
    SLEEVE_ORDER,
    SLIT_ORDER,
    BackCoverage,
    NecklineModesty,
    SleeveCoverage,
    SlitCoverage,
    coverage_rank,
)


class ModestyBadge(str, Enum):
    """Badges surfaced on product cards and detail pages."""

    FULLY_LINED = "fully_lined"
    OPAQUE_FABRIC = "opaque_fabric"
    FULL_COVERAGE = "full_coverage"
    MODEST_NECKLINE = "modest_neckline"
    COVERED_BACK = "covered_back"
    FULL_SLEEVES = "full_sleeves"
    NO_SLIT = "no_slit"


class ModestyAdvisory(str, Enum):
    """Honest disclosures. Shown alongside badges, never suppressed.

    A luxury modest-wear brand earns trust by disclosing what a garment is not,
    as much as by advertising what it is.
    """

    SLIP_REQUIRED = "slip_required"
    SHEER_OVERLAY = "sheer_overlay"
    SLEEVELESS = "sleeveless"
    OPEN_BACK = "open_back"
    HIGH_SLIT = "high_slit"
    DEEP_NECKLINE = "deep_neckline"


#: Human-readable labels. Kept next to the enum so they cannot fall out of sync.
BADGE_LABELS: dict[ModestyBadge, str] = {
    ModestyBadge.FULLY_LINED: "Fully lined",
    ModestyBadge.OPAQUE_FABRIC: "Opaque fabric",
    ModestyBadge.FULL_COVERAGE: "Full coverage",
    ModestyBadge.MODEST_NECKLINE: "Modest neckline",
    ModestyBadge.COVERED_BACK: "Covered back",
    ModestyBadge.FULL_SLEEVES: "Full sleeves",
    ModestyBadge.NO_SLIT: "No slit",
}

ADVISORY_LABELS: dict[ModestyAdvisory, str] = {
    ModestyAdvisory.SLIP_REQUIRED: "Slip required",
    ModestyAdvisory.SHEER_OVERLAY: "Sheer overlay",
    ModestyAdvisory.SLEEVELESS: "Sleeveless",
    ModestyAdvisory.OPEN_BACK: "Open back",
    ModestyAdvisory.HIGH_SLIT: "High slit",
    ModestyAdvisory.DEEP_NECKLINE: "Deep neckline",
}


@dataclass(frozen=True, slots=True)
class ModestyProfile:
    """The modesty attributes of a garment, independent of the ORM."""

    is_opaque: bool
    has_full_lining: bool
    slit_coverage: str
    sleeve_coverage: str
    neckline_modesty: str
    back_coverage: str
    requires_slip: bool = False
    is_sheer_overlay_only: bool = False


@dataclass(frozen=True, slots=True)
class ModestyAssessment:
    """Derived, display-ready modesty information."""

    badges: tuple[ModestyBadge, ...]
    advisories: tuple[ModestyAdvisory, ...]
    #: 0-100. A coarse sort/filter key, never a substitute for the badges.
    coverage_score: int

    def as_dict(self) -> dict[str, object]:
        return {
            "badges": [
                {"code": b.value, "label": BADGE_LABELS[b]} for b in self.badges
            ],
            "advisories": [
                {"code": a.value, "label": ADVISORY_LABELS[a]} for a in self.advisories
            ],
            "coverage_score": self.coverage_score,
        }


def derive_modesty(profile: ModestyProfile) -> ModestyAssessment:
    """Derive badges, advisories and a coverage score from raw attributes.

    Rules are intentionally conservative: a badge is awarded only when the
    garment unambiguously qualifies. Over-claiming coverage is the failure mode
    that loses a modest-wear customer permanently.
    """
    badges: list[ModestyBadge] = []
    advisories: list[ModestyAdvisory] = []

    slit_rank = coverage_rank(profile.slit_coverage, SLIT_ORDER)
    sleeve_rank = coverage_rank(profile.sleeve_coverage, SLEEVE_ORDER)
    neck_rank = coverage_rank(profile.neckline_modesty, NECKLINE_ORDER)
    back_rank = coverage_rank(profile.back_coverage, BACK_ORDER)

    # --- Badges ------------------------------------------------------------
    # A sheer overlay is never "fully lined" however the lining flag is set;
    # the overlay is the garment the customer sees.
    if profile.has_full_lining and not profile.is_sheer_overlay_only:
        badges.append(ModestyBadge.FULLY_LINED)

    if profile.is_opaque and not profile.is_sheer_overlay_only:
        badges.append(ModestyBadge.OPAQUE_FABRIC)

    if profile.sleeve_coverage in (SleeveCoverage.FULL, SleeveCoverage.EXTRA_LONG):
        badges.append(ModestyBadge.FULL_SLEEVES)

    if profile.slit_coverage == SlitCoverage.NONE:
        badges.append(ModestyBadge.NO_SLIT)

    if profile.neckline_modesty in (NecklineModesty.HIGH, NecklineModesty.CLOSED):
        badges.append(ModestyBadge.MODEST_NECKLINE)

    if profile.back_coverage in (BackCoverage.MODERATE, BackCoverage.FULL):
        badges.append(ModestyBadge.COVERED_BACK)

    # FULL_COVERAGE is the strongest claim and requires every dimension to
    # qualify simultaneously, including opacity and lining.
    fully_covered = (
        profile.is_opaque
        and profile.has_full_lining
        and not profile.is_sheer_overlay_only
        and not profile.requires_slip
        and profile.sleeve_coverage in (SleeveCoverage.FULL, SleeveCoverage.EXTRA_LONG)
        and profile.slit_coverage in (SlitCoverage.NONE, SlitCoverage.ANKLE)
        and profile.neckline_modesty in (NecklineModesty.HIGH, NecklineModesty.CLOSED)
        and profile.back_coverage in (BackCoverage.MODERATE, BackCoverage.FULL)
    )
    if fully_covered:
        badges.append(ModestyBadge.FULL_COVERAGE)

    # --- Advisories --------------------------------------------------------
    if profile.requires_slip:
        advisories.append(ModestyAdvisory.SLIP_REQUIRED)
    if profile.is_sheer_overlay_only:
        advisories.append(ModestyAdvisory.SHEER_OVERLAY)
    if profile.sleeve_coverage == SleeveCoverage.SLEEVELESS:
        advisories.append(ModestyAdvisory.SLEEVELESS)
    if profile.back_coverage in (BackCoverage.OPEN, BackCoverage.DEEP):
        advisories.append(ModestyAdvisory.OPEN_BACK)
    if profile.slit_coverage in (SlitCoverage.THIGH, SlitCoverage.KNEE):
        advisories.append(ModestyAdvisory.HIGH_SLIT)
    if profile.neckline_modesty == NecklineModesty.DEEP:
        advisories.append(ModestyAdvisory.DEEP_NECKLINE)

    # --- Coverage score ----------------------------------------------------
    # Weighted so the dimensions customers ask about most carry the most
    # influence. Opacity and lining are gating factors, not additive extras.
    max_slit = len(SLIT_ORDER) - 1
    max_sleeve = len(SLEEVE_ORDER) - 1
    max_neck = len(NECKLINE_ORDER) - 1
    max_back = len(BACK_ORDER) - 1

    weighted = (
        (slit_rank / max_slit) * 25
        + (sleeve_rank / max_sleeve) * 30
        + (neck_rank / max_neck) * 25
        + (back_rank / max_back) * 20
    )
    if not profile.is_opaque:
        weighted *= 0.5
    if profile.is_sheer_overlay_only:
        weighted *= 0.5
    if profile.requires_slip:
        weighted *= 0.85

    return ModestyAssessment(
        badges=tuple(badges),
        advisories=tuple(advisories),
        coverage_score=int(round(max(0.0, min(100.0, weighted)))),
    )
