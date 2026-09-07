"""Integration tests for the GST quotation HTTP surface."""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def quote(client, **overrides):
    payload = {
        "country_code": "IN",
        "state_code": "MH",
        "lines": [{"sku": "KS-001", "hsn_code": "6204", "unit_price": "10000.00", "quantity": 1}],
    }
    payload.update(overrides)
    return client.post(reverse("taxes:tax-quote"), payload, format="json")


class TestTaxQuoteEndpoint:
    def test_anonymous_callers_may_quote(self, api_client):
        assert quote(api_client).status_code == 200

    def test_maharashtra_returns_cgst_sgst(self, api_client):
        data = quote(api_client).data
        assert data["supply_type"] == "intra_state"
        assert data["cgst_total"] == "900.00"
        assert data["sgst_total"] == "900.00"
        assert data["igst_total"] == "0.00"
        assert data["grand_total"] == "11800.00"

    def test_other_state_returns_igst(self, api_client):
        data = quote(api_client, state_code="DL").data
        assert data["supply_type"] == "inter_state"
        assert data["igst_total"] == "1800.00"
        assert data["cgst_total"] == "0.00"

    def test_export_is_zero_rated(self, api_client):
        data = quote(api_client, country_code="AE", state_code="").data
        assert data["supply_type"] == "export"
        assert data["tax_total"] == "0.00"
        assert data["is_zero_rated_export"] is True
        assert data["grand_total"] == "10000.00"

    def test_missing_state_for_india_is_400(self, api_client):
        response = quote(api_client, state_code="")
        assert response.status_code == 400
        assert "place_of_supply" in response.data

    def test_unknown_state_is_400(self, api_client):
        assert quote(api_client, state_code="ZZ").status_code == 400

    def test_historical_quote_uses_old_regime(self, api_client):
        """A credit note against a 2025 order must reproduce the old rate."""
        data = quote(api_client, as_of="2025-06-01").data
        assert "GST 1.0" in data["regime"]
        assert data["cgst_total"] == "600.00"
        assert data["grand_total"] == "11200.00"

    def test_current_quote_uses_gst_two_point_zero(self, api_client):
        data = quote(api_client).data
        assert "GST 2.0" in data["regime"]

    def test_unlawful_rate_override_is_400(self, api_client):
        response = quote(
            api_client,
            lines=[{"sku": "X", "hsn_code": "6204", "unit_price": "100.00", "rate_override": "7"}],
        )
        assert response.status_code == 400

    def test_unknown_hsn_is_400_not_500(self, api_client):
        response = quote(
            api_client, lines=[{"sku": "X", "hsn_code": "0000", "unit_price": "100.00"}]
        )
        assert response.status_code == 400

    def test_empty_lines_rejected(self, api_client):
        assert quote(api_client, lines=[]).status_code == 400

    def test_negative_price_rejected(self, api_client):
        response = quote(
            api_client, lines=[{"sku": "X", "hsn_code": "6204", "unit_price": "-5.00"}]
        )
        assert response.status_code == 400

    def test_shipping_included_in_grand_total(self, api_client):
        data = quote(api_client, shipping_charge="500.00").data
        assert data["grand_total"] == "12390.00"

    def test_mixed_basket_rate_summary(self, api_client):
        data = quote(
            api_client,
            lines=[
                {"sku": "LEHENGA", "hsn_code": "6211", "unit_price": "48000.00"},
                {"sku": "DUPATTA", "hsn_code": "6214", "unit_price": "900.00"},
                {"sku": "FIT", "hsn_code": "998821", "unit_price": "2500.00"},
            ],
        ).data
        rates = {row["rate"] for row in data["rate_summary"]}
        assert rates == {"5", "18"}
        assert data["tax_total"] == "8810.00"

    def test_response_is_fully_string_serialised(self, api_client):
        """No floats may reach the wire - amounts must be decimal strings."""
        data = quote(api_client).data
        for key in ("taxable_value", "cgst_total", "sgst_total", "igst_total", "grand_total"):
            assert isinstance(data[key], str), f"{key} must be a string, got {type(data[key])}"


class TestTaxReferenceEndpoint:
    def test_reference_card_is_public(self, api_client):
        response = api_client.get(reverse("taxes:tax-reference"))
        assert response.status_code == 200
        assert response.data["home_state_code"] == "MH"
        assert response.data["apparel_slab"]["threshold_per_piece"] == "2500.00"
        assert response.data["apparel_slab"]["rate_above"] == "18"
        assert "GST 2.0" in response.data["regime"]
        assert "MH" in response.data["supported_states"]

    def test_reference_exposes_regime_history(self, api_client):
        data = api_client.get(reverse("taxes:tax-reference")).data
        assert len(data["regime_history"]) >= 2
        assert data["regime_history"][-1]["effective_from"] == "2025-09-22"

    def test_abolished_12_percent_not_offered(self, api_client):
        data = api_client.get(reverse("taxes:tax-reference")).data
        assert "12" not in data["permitted_rates"]


class TestHealthEndpoints:
    def test_health_is_public_and_cheap(self, api_client):
        response = api_client.get(reverse("health"))
        assert response.status_code == 200
        assert response.data["status"] == "ok"

    def test_readiness_checks_dependencies(self, api_client):
        response = api_client.get(reverse("ready"))
        assert response.status_code == 200
        assert response.data["checks"]["database"] == "ok"
        assert response.data["checks"]["cache"] == "ok"
