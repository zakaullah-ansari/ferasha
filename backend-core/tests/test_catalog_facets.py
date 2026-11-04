"""Facet counts drive the storefront's filter panel: they must be true.

Regression: an explicit order_by on the list queryset leaked into the
values().annotate() GROUP BY, so every product became its own group and
every count came back as 1.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.catalog.enums import Occasion, SleeveCoverage, SlitCoverage
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

FACETS = reverse("catalog:product-facets")
PRODUCTS = reverse("catalog:product-list")


@pytest.fixture
def catalogue():
    # Three bridal pieces and one Eid piece: shared values must add up.
    for _ in range(3):
        make_variant(product=make_product(occasion=Occasion.BRIDAL))
    make_variant(
        product=make_product(
            occasion=Occasion.EID,
            sleeve_coverage=SleeveCoverage.ELBOW,
            slit_coverage=SlitCoverage.KNEE,
        )
    )


def test_shared_values_are_counted_together(api_client, catalogue):
    data = api_client.get(FACETS).json()

    assert data["total"] == 4
    assert {o["value"]: o["count"] for o in data["occasion"]} == {"bridal": 3, "eid": 1}
    assert sum(o["count"] for o in data["occasion"]) == data["total"]


def test_options_carry_enum_labels_in_enum_order(api_client, catalogue):
    occasion = api_client.get(FACETS).json()["occasion"]

    assert [o["label"] for o in occasion] == ["Bridal", "Eid"]  # enum order, not count order


@pytest.mark.parametrize("facet", ["fully_covered", "has_full_lining", "is_opaque", "full_sleeves", "no_slit"])
def test_modesty_counts_match_what_the_filter_returns(api_client, catalogue, facet):
    counts = {o["value"]: o["count"] for o in api_client.get(FACETS).json()["modesty"]}

    listed = api_client.get(PRODUCTS, {facet: "true"}).json()["count"]

    assert counts[facet] == listed


def test_counts_follow_the_active_filters(api_client, catalogue):
    data = api_client.get(FACETS, {"occasion": "eid"}).json()

    assert data["total"] == 1
    assert [o["value"] for o in data["occasion"]] == ["eid"]
