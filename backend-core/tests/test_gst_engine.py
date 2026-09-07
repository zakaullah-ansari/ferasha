"""Unit tests for the pure-Python GST engine. No Django required."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.taxes.constants import resolve_regime  # noqa: E402
from apps.taxes.services import (  # noqa: E402
    PlaceOfSupply,
    SupplyType,
    TaxError,
    TaxableLine,
    calculate_gst,
    calculate_line_tax,
    resolve_gst_rate,
)

MUMBAI = PlaceOfSupply(country_code="IN", state_code="MH")
DELHI = PlaceOfSupply(country_code="IN", state_code="DL")
DUBAI = PlaceOfSupply(country_code="AE")


def suit(price: str, qty: int = 1, **kw) -> TaxableLine:
    return TaxableLine(sku="KS-001", hsn_code="6204", unit_price=Decimal(price), quantity=qty, **kw)


class TestRateResolution:
    """Current regime: GST 2.0, w.e.f. 22 Sep 2025. 5% to Rs.2500, 18% above."""

    def test_apparel_at_or_below_2500_is_five_percent(self):
        rate, source = resolve_gst_rate(suit("2499.00"))
        assert rate == Decimal("5")
        assert source == "slab:6204:<=2500"

    def test_boundary_exactly_2500_is_five_percent(self):
        assert resolve_gst_rate(suit("2500.00"))[0] == Decimal("5")

    def test_apparel_above_2500_is_eighteen_percent(self):
        assert resolve_gst_rate(suit("2500.01"))[0] == Decimal("18")

    def test_old_1000_threshold_no_longer_applies(self):
        """A Rs.1500 kameez was 12% pre-reform; it is 5% now."""
        assert resolve_gst_rate(suit("1500.00"))[0] == Decimal("5")

    def test_slab_uses_post_discount_per_piece_value(self):
        line = suit("3000.00", qty=2, discount=Decimal("1200.00"))
        # (3000*2 - 1200) / 2 = 2400 per piece -> 5%
        assert resolve_gst_rate(line)[0] == Decimal("5")

    def test_dotted_hsn_resolves_by_chapter_heading(self):
        line = TaxableLine(sku="L", hsn_code="6204.42.00", unit_price=Decimal("5000"))
        assert resolve_gst_rate(line)[0] == Decimal("18")

    def test_tailoring_service_is_five_percent(self):
        line = TaxableLine(sku="BESPOKE", hsn_code="998821", unit_price=Decimal("300"))
        rate, source = resolve_gst_rate(line)
        assert rate == Decimal("5")
        assert source == "flat:998821"

    def test_unstitched_fabric_is_flat_five_percent(self):
        line = TaxableLine(sku="FAB", hsn_code="5208", unit_price=Decimal("9000"))
        assert resolve_gst_rate(line)[0] == Decimal("5")

    def test_override_wins_over_slab(self):
        line = suit("5000.00", rate_override=Decimal("5"))
        assert resolve_gst_rate(line) == (Decimal("5"), "override")

    def test_unlawful_override_rejected(self):
        with pytest.raises(TaxError, match="not a lawful GST rate"):
            suit("100.00", rate_override=Decimal("7"))

    def test_abolished_12_percent_slab_is_rejected(self):
        """12% no longer exists for textiles; an override to it must fail."""
        with pytest.raises(TaxError, match="not a lawful GST rate"):
            suit("100.00", rate_override=Decimal("12"))


class TestRegimeHistory:
    """Invoices must be reproducible under the regime in force at supply time."""

    PRE = date(2025, 6, 1)
    POST = date(2026, 1, 1)

    def test_pre_reform_1500_garment_was_twelve_percent(self):
        line = suit("1500.00", as_of=self.PRE)
        assert resolve_gst_rate(line)[0] == Decimal("12")

    def test_post_reform_same_garment_is_five_percent(self):
        line = suit("1500.00", as_of=self.POST)
        assert resolve_gst_rate(line)[0] == Decimal("5")

    def test_pre_reform_premium_garment_was_twelve_percent(self):
        assert resolve_gst_rate(suit("40000.00", as_of=self.PRE))[0] == Decimal("12")

    def test_post_reform_premium_garment_is_eighteen_percent(self):
        assert resolve_gst_rate(suit("40000.00", as_of=self.POST))[0] == Decimal("18")

    def test_changeover_date_is_inclusive(self):
        assert resolve_regime(date(2025, 9, 21)).apparel_threshold == Decimal("1000.00")
        assert resolve_regime(date(2025, 9, 22)).apparel_threshold == Decimal("2500.00")

    def test_twelve_percent_override_legal_under_old_regime(self):
        line = suit("100.00", rate_override=Decimal("12"), as_of=self.PRE)
        assert line.rate_override == Decimal("12")

    def test_breakdown_records_the_regime_applied(self):
        b = calculate_gst([suit("40000.00")], MUMBAI, as_of=self.POST)
        assert "GST 2.0" in b.regime_name
        old = calculate_gst([suit("40000.00")], MUMBAI, as_of=self.PRE)
        assert "GST 1.0" in old.regime_name

    def test_as_of_propagates_to_lines_without_a_date(self):
        b = calculate_gst([suit("1500.00")], MUMBAI, as_of=self.PRE)
        assert b.lines[0].gst_rate == Decimal("12")

    def test_date_before_gst_existed_is_rejected(self):
        with pytest.raises(ValueError, match="No GST regime"):
            resolve_regime(date(2010, 1, 1))

    def test_unknown_hsn_raises(self):
        line = TaxableLine(sku="X", hsn_code="9999", unit_price=Decimal("100"))
        with pytest.raises(TaxError, match="no GST rate could be resolved"):
            resolve_gst_rate(line)


class TestRouting:
    def test_maharashtra_splits_cgst_sgst(self):
        r = calculate_line_tax(suit("10000.00"), MUMBAI)
        assert r.gst_rate == Decimal("18")
        assert r.cgst_rate == r.sgst_rate == Decimal("9")
        assert r.cgst_amount == Decimal("900.00")
        assert r.sgst_amount == Decimal("900.00")
        assert r.igst_amount == Decimal("0.00")
        assert r.total_tax == Decimal("1800.00")
        assert r.line_total == Decimal("11800.00")

    def test_rest_of_india_levies_igst(self):
        r = calculate_line_tax(suit("10000.00"), DELHI)
        assert r.igst_rate == Decimal("18")
        assert r.igst_amount == Decimal("1800.00")
        assert r.cgst_amount == r.sgst_amount == Decimal("0.00")

    def test_export_is_zero_rated(self):
        r = calculate_line_tax(suit("10000.00"), DUBAI)
        assert r.gst_rate == Decimal("0")
        assert r.total_tax == Decimal("0.00")
        assert r.line_total == Decimal("10000.00")
        assert r.rate_source == "export:zero-rated"

    def test_supply_type_classification(self):
        assert MUMBAI.supply_type is SupplyType.INTRA_STATE
        assert DELHI.supply_type is SupplyType.INTER_STATE
        assert DUBAI.supply_type is SupplyType.EXPORT

    def test_cgst_plus_sgst_equals_igst_for_same_rate(self):
        mh = calculate_line_tax(suit("7999.00"), MUMBAI)
        dl = calculate_line_tax(suit("7999.00"), DELHI)
        assert mh.cgst_amount + mh.sgst_amount == dl.igst_amount

    def test_state_gst_numeric_codes(self):
        assert MUMBAI.state_gst_code == "27"
        assert DELHI.state_gst_code == "07"

    def test_domestic_requires_state(self):
        with pytest.raises(TaxError, match="state_code is required"):
            PlaceOfSupply(country_code="IN")

    def test_unknown_state_rejected(self):
        with pytest.raises(TaxError, match="Unknown Indian state"):
            PlaceOfSupply(country_code="IN", state_code="ZZ")

    def test_bad_country_rejected(self):
        with pytest.raises(TaxError, match="alpha-2"):
            PlaceOfSupply(country_code="IND")


class TestInclusivePricing:
    def test_tax_inclusive_backs_out_correctly(self):
        line = suit("11800.00", price_is_tax_inclusive=True)
        r = calculate_line_tax(line, MUMBAI)
        assert r.gst_rate == Decimal("18")
        assert r.taxable_value == Decimal("10000.00")
        assert r.total_tax == Decimal("1800.00")
        assert r.line_total == Decimal("11800.00")

    def test_inclusive_near_slab_boundary_converges(self):
        # 2625 inclusive: at 5% net is 2500.00 (<=2500 -> 5% is consistent)
        line = suit("2625.00", price_is_tax_inclusive=True)
        r = calculate_line_tax(line, MUMBAI)
        assert r.gst_rate == Decimal("5")
        assert r.taxable_value == Decimal("2500.00")


class TestOrderTotals:
    def test_mixed_order_totals_and_summary(self):
        lines = [
            TaxableLine(sku="LEHENGA", hsn_code="6211", unit_price=Decimal("48000.00")),
            TaxableLine(sku="DUPATTA", hsn_code="6214", unit_price=Decimal("900.00")),
            TaxableLine(sku="FIT", hsn_code="998821", unit_price=Decimal("2500.00")),
        ]
        b = calculate_gst(lines, MUMBAI)
        assert b.taxable_value == Decimal("51400.00")
        # 48000*18% = 8640 ; 900*5% = 45 ; 2500 tailoring*5% = 125
        assert b.tax_total == Decimal("8810.00")
        assert b.cgst_total == b.sgst_total == Decimal("4405.00")
        assert b.igst_total == Decimal("0.00")
        assert b.grand_total == Decimal("60210.00")
        assert {r[0] for r in b.rate_summary} == {Decimal("5"), Decimal("18")}

    def test_shipping_taxed_at_principal_rate(self):
        b = calculate_gst([suit("10000.00")], DELHI, shipping_charge=Decimal("500.00"))
        ship = b.lines[-1]
        assert ship.sku == "SHIPPING"
        assert ship.gst_rate == Decimal("18")
        assert ship.igst_amount == Decimal("90.00")
        assert b.grand_total == Decimal("12390.00")

    def test_export_order_has_zero_tax_and_note(self):
        b = calculate_gst([suit("25000.00")], DUBAI, shipping_charge=Decimal("3000.00"))
        assert b.tax_total == Decimal("0.00")
        assert b.grand_total == Decimal("28000.00")
        assert b.is_zero_rated_export is True
        assert any("Zero-rated export" in n for n in b.notes)

    def test_totals_are_internally_consistent(self):
        b = calculate_gst(
            [suit("3333.33", qty=3, discount=Decimal("777.77"))], MUMBAI,
            shipping_charge=Decimal("199.99"),
        )
        assert b.cgst_total + b.sgst_total + b.igst_total == b.tax_total
        assert b.taxable_value + b.tax_total == b.grand_total
        assert sum(l.total_tax for l in b.lines) == b.tax_total

    def test_serialisation_is_json_safe(self):
        import json

        b = calculate_gst([suit("10000.00")], MUMBAI)
        assert json.loads(json.dumps(b.as_dict()))["supply_type"] == "intra_state"

    def test_empty_order_rejected(self):
        with pytest.raises(TaxError, match="At least one taxable line"):
            calculate_gst([], MUMBAI)


class TestValidation:
    def test_negative_price_rejected(self):
        with pytest.raises(TaxError, match="must not be negative"):
            suit("-1.00")

    def test_zero_quantity_rejected(self):
        with pytest.raises(TaxError, match="quantity must be >= 1"):
            suit("100.00", qty=0)

    def test_discount_exceeding_gross_rejected(self):
        with pytest.raises(TaxError, match="exceeds line gross"):
            suit("100.00", discount=Decimal("200.00"))

    def test_missing_hsn_rejected(self):
        with pytest.raises(TaxError, match="hsn_code is required"):
            TaxableLine(sku="X", hsn_code="  ", unit_price=Decimal("10"))

    def test_negative_shipping_rejected(self):
        with pytest.raises(TaxError, match="shipping_charge must not be negative"):
            calculate_gst([suit("100.00")], MUMBAI, shipping_charge=Decimal("-1"))
