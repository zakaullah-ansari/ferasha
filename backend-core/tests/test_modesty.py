"""Truth-table tests for modesty badge derivation.

These rules are user-facing promises. A garment badged "full coverage" that is
not loses a modest-wear customer permanently, so the tests are exhaustive on
the boundary conditions rather than illustrative.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.catalog.enums import (  # noqa: E402
    BackCoverage,
    NecklineModesty,
    SleeveCoverage,
    SlitCoverage,
)
from apps.catalog.modesty import (  # noqa: E402
    ModestyAdvisory,
    ModestyBadge,
    ModestyProfile,
    derive_modesty,
)

pytestmark = pytest.mark.unit


def profile(**overrides) -> ModestyProfile:
    """A fully covering garment; override single attributes to test each rule."""
    base = dict(
        is_opaque=True,
        has_full_lining=True,
        slit_coverage=SlitCoverage.NONE,
        sleeve_coverage=SleeveCoverage.FULL,
        neckline_modesty=NecklineModesty.HIGH,
        back_coverage=BackCoverage.FULL,
        requires_slip=False,
        is_sheer_overlay_only=False,
    )
    base.update(overrides)
    return ModestyProfile(**base)


class TestFullCoverage:
    """FULL_COVERAGE is the strongest claim; every dimension must qualify."""

    def test_ideal_garment_earns_full_coverage(self):
        assert ModestyBadge.FULL_COVERAGE in derive_modesty(profile()).badges

    @pytest.mark.parametrize(
        "override",
        [
            {"is_opaque": False},
            {"has_full_lining": False},
            {"requires_slip": True},
            {"sleeve_coverage": SleeveCoverage.THREE_QUARTER},
            {"sleeve_coverage": SleeveCoverage.SLEEVELESS},
            {"slit_coverage": SlitCoverage.MID_CALF},
            {"slit_coverage": SlitCoverage.THIGH},
            {"neckline_modesty": NecklineModesty.MODERATE},
            {"neckline_modesty": NecklineModesty.DEEP},
            {"back_coverage": BackCoverage.DEEP},
            {"back_coverage": BackCoverage.OPEN},
        ],
        ids=lambda d: "-".join(f"{k}={v}" for k, v in d.items()),
    )
    def test_any_single_failure_revokes_full_coverage(self, override):
        """One failing dimension is enough to withhold the badge."""
        assert ModestyBadge.FULL_COVERAGE not in derive_modesty(profile(**override)).badges

    def test_ankle_slit_still_qualifies(self):
        """An ankle slit is a construction detail, not an immodesty."""
        result = derive_modesty(profile(slit_coverage=SlitCoverage.ANKLE))
        assert ModestyBadge.FULL_COVERAGE in result.badges

    def test_extra_long_sleeve_qualifies(self):
        result = derive_modesty(profile(sleeve_coverage=SleeveCoverage.EXTRA_LONG))
        assert ModestyBadge.FULL_COVERAGE in result.badges

    def test_closed_neckline_qualifies(self):
        result = derive_modesty(profile(neckline_modesty=NecklineModesty.CLOSED))
        assert ModestyBadge.FULL_COVERAGE in result.badges


class TestIndividualBadges:
    def test_fully_lined(self):
        assert ModestyBadge.FULLY_LINED in derive_modesty(profile()).badges
        assert (
            ModestyBadge.FULLY_LINED
            not in derive_modesty(profile(has_full_lining=False)).badges
        )

    def test_sheer_overlay_never_counts_as_lined(self):
        """The overlay is the garment the customer sees."""
        result = derive_modesty(
            profile(has_full_lining=True, is_opaque=False, is_sheer_overlay_only=True)
        )
        assert ModestyBadge.FULLY_LINED not in result.badges
        assert ModestyBadge.OPAQUE_FABRIC not in result.badges
        assert ModestyAdvisory.SHEER_OVERLAY in result.advisories

    def test_opaque_fabric(self):
        assert ModestyBadge.OPAQUE_FABRIC in derive_modesty(profile()).badges
        assert (
            ModestyBadge.OPAQUE_FABRIC not in derive_modesty(profile(is_opaque=False)).badges
        )

    @pytest.mark.parametrize(
        "sleeve,expected",
        [
            (SleeveCoverage.FULL, True),
            (SleeveCoverage.EXTRA_LONG, True),
            (SleeveCoverage.THREE_QUARTER, False),
            (SleeveCoverage.ELBOW, False),
            (SleeveCoverage.SLEEVELESS, False),
        ],
    )
    def test_full_sleeves(self, sleeve, expected):
        badges = derive_modesty(profile(sleeve_coverage=sleeve)).badges
        assert (ModestyBadge.FULL_SLEEVES in badges) is expected

    @pytest.mark.parametrize(
        "slit,expected",
        [
            (SlitCoverage.NONE, True),
            (SlitCoverage.ANKLE, False),
            (SlitCoverage.KNEE, False),
            (SlitCoverage.THIGH, False),
        ],
    )
    def test_no_slit_badge_is_literal(self, slit, expected):
        badges = derive_modesty(profile(slit_coverage=slit)).badges
        assert (ModestyBadge.NO_SLIT in badges) is expected

    @pytest.mark.parametrize(
        "neck,expected",
        [
            (NecklineModesty.CLOSED, True),
            (NecklineModesty.HIGH, True),
            (NecklineModesty.MODERATE, False),
            (NecklineModesty.DEEP, False),
        ],
    )
    def test_modest_neckline(self, neck, expected):
        badges = derive_modesty(profile(neckline_modesty=neck)).badges
        assert (ModestyBadge.MODEST_NECKLINE in badges) is expected

    @pytest.mark.parametrize(
        "back,expected",
        [
            (BackCoverage.FULL, True),
            (BackCoverage.MODERATE, True),
            (BackCoverage.DEEP, False),
            (BackCoverage.OPEN, False),
        ],
    )
    def test_covered_back(self, back, expected):
        badges = derive_modesty(profile(back_coverage=back)).badges
        assert (ModestyBadge.COVERED_BACK in badges) is expected


class TestAdvisories:
    """Honest disclosure. Advisories must never be suppressed by a badge."""

    def test_slip_required(self):
        result = derive_modesty(profile(requires_slip=True))
        assert ModestyAdvisory.SLIP_REQUIRED in result.advisories

    def test_sleeveless(self):
        result = derive_modesty(profile(sleeve_coverage=SleeveCoverage.SLEEVELESS))
        assert ModestyAdvisory.SLEEVELESS in result.advisories

    def test_open_back(self):
        assert (
            ModestyAdvisory.OPEN_BACK
            in derive_modesty(profile(back_coverage=BackCoverage.OPEN)).advisories
        )
        assert (
            ModestyAdvisory.OPEN_BACK
            in derive_modesty(profile(back_coverage=BackCoverage.DEEP)).advisories
        )

    def test_high_slit(self):
        for slit in (SlitCoverage.THIGH, SlitCoverage.KNEE):
            assert (
                ModestyAdvisory.HIGH_SLIT
                in derive_modesty(profile(slit_coverage=slit)).advisories
            )

    def test_deep_neckline(self):
        result = derive_modesty(profile(neckline_modesty=NecklineModesty.DEEP))
        assert ModestyAdvisory.DEEP_NECKLINE in result.advisories

    def test_ideal_garment_has_no_advisories(self):
        assert derive_modesty(profile()).advisories == ()

    def test_advisory_coexists_with_badges(self):
        """A slip-required garment can still be opaque and full-sleeved."""
        result = derive_modesty(profile(requires_slip=True))
        assert ModestyAdvisory.SLIP_REQUIRED in result.advisories
        assert ModestyBadge.FULL_SLEEVES in result.badges
        assert ModestyBadge.FULL_COVERAGE not in result.badges


class TestCoverageScore:
    def test_maximally_covering_scores_100(self):
        result = derive_modesty(
            profile(
                sleeve_coverage=SleeveCoverage.EXTRA_LONG,
                neckline_modesty=NecklineModesty.CLOSED,
                back_coverage=BackCoverage.FULL,
                slit_coverage=SlitCoverage.NONE,
            )
        )
        assert result.coverage_score == 100

    def test_minimally_covering_scores_low(self):
        result = derive_modesty(
            profile(
                is_opaque=False,
                has_full_lining=False,
                sleeve_coverage=SleeveCoverage.SLEEVELESS,
                neckline_modesty=NecklineModesty.DEEP,
                back_coverage=BackCoverage.OPEN,
                slit_coverage=SlitCoverage.THIGH,
            )
        )
        assert result.coverage_score == 0

    def test_sheer_halves_the_score(self):
        opaque = derive_modesty(profile()).coverage_score
        sheer = derive_modesty(profile(is_opaque=False)).coverage_score
        assert sheer == pytest.approx(opaque / 2, abs=1)

    def test_score_is_bounded(self):
        for prof in (profile(), profile(is_opaque=False, requires_slip=True)):
            assert 0 <= derive_modesty(prof).coverage_score <= 100

    def test_more_coverage_scores_higher(self):
        low = derive_modesty(
            profile(sleeve_coverage=SleeveCoverage.SLEEVELESS)
        ).coverage_score
        high = derive_modesty(profile(sleeve_coverage=SleeveCoverage.FULL)).coverage_score
        assert high > low


class TestSerialisation:
    def test_as_dict_is_json_safe(self):
        import json

        payload = derive_modesty(profile(requires_slip=True)).as_dict()
        round_tripped = json.loads(json.dumps(payload))
        assert round_tripped["coverage_score"] >= 0
        assert all("code" in b and "label" in b for b in round_tripped["badges"])

    def test_every_badge_has_a_label(self):
        from apps.catalog.modesty import ADVISORY_LABELS, BADGE_LABELS

        assert set(BADGE_LABELS) == set(ModestyBadge)
        assert set(ADVISORY_LABELS) == set(ModestyAdvisory)
