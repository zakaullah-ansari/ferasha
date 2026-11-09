"""Catalogue search, the way shoppers type.

Every word counts (in any order), spelling slips and regional variants still
find the piece, codes like raw_silk read as words, and a match in the name
outranks a passing mention in a description.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.catalog.enums import Fabric, GarmentType, Occasion, WorkType
from tests.factories import make_category, make_product, make_variant

pytestmark = pytest.mark.django_db

PRODUCTS = reverse("catalog:product-list")
FACETS = reverse("catalog:product-facets")


@pytest.fixture
def catalogue():
    bridal = make_category(name="Bridal", slug="bridal-search")
    suits = make_category(name="Suits", slug="suits-search")
    everyday = {"occasion": Occasion.CASUAL}  # the factory's default occasion is bridal
    items = {
        "gharara": make_product(name="Velvet Gharara Set - Emerald", fabric=Fabric.VELVET, garment_type=GarmentType.GHARARA, category=bridal),
        "lehenga": make_product(name="Banarasi Bridal Lehenga - Crimson", fabric=Fabric.BANARASI, garment_type=GarmentType.LEHENGA, category=bridal),
        "kurta": make_product(name="Lucknowi Kurta Set - Ivory", fabric=Fabric.COTTON, work_type=WorkType.CHIKANKARI, category=suits, **everyday),
        "blouse": make_product(name="Deep-Back Blouse - Gold", fabric=Fabric.RAW_SILK, category=suits, **everyday),
        "mention": make_product(
            name="Printed Lawn Suit - Mint",
            fabric=Fabric.LAWN,
            description="Pairs beautifully with a gharara for mehndi.",
            category=suits,
            **everyday,
        ),
    }
    for product in items.values():
        make_variant(product=product)
    return items


def names(client, term, **params):
    return [row["name"] for row in client.get(PRODUCTS, {"search": term, **params}).json()["results"]]


def test_every_word_counts_in_any_order(api_client, catalogue):
    assert names(api_client, "gharara velvet") == ["Velvet Gharara Set - Emerald"]
    assert names(api_client, "velvet lehenga") == []  # both words must match the same piece


@pytest.mark.parametrize("term", ["gharra", "lehnga", "chikenkari", "banarsi"])
def test_spelling_slips_still_find_the_piece(api_client, catalogue, term):
    assert names(api_client, term), term


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("garara", "Velvet Gharara Set - Emerald"),
        ("lahanga", "Banarasi Bridal Lehenga - Crimson"),
        ("chikan", "Lucknowi Kurta Set - Ivory"),
        ("kurti", "Lucknowi Kurta Set - Ivory"),
    ],
)
def test_regional_variants_are_the_same_word(api_client, catalogue, term, expected):
    assert expected in names(api_client, term)


def test_stored_codes_read_as_words(api_client, catalogue):
    assert names(api_client, "raw silk") == ["Deep-Back Blouse - Gold"]


def test_a_name_match_outranks_a_mention(api_client, catalogue):
    assert names(api_client, "gharara") == ["Velvet Gharara Set - Emerald", "Printed Lawn Suit - Mint"]


def test_a_chosen_sort_still_wins(api_client, catalogue):
    by_name = names(api_client, "gharara", ordering="name")
    assert by_name == ["Printed Lawn Suit - Mint", "Velvet Gharara Set - Emerald"]


def test_the_category_and_occasion_are_searched(api_client, catalogue):
    assert set(names(api_client, "bridal")) == {"Velvet Gharara Set - Emerald", "Banarasi Bridal Lehenga - Crimson"}


def test_blank_search_returns_everything(api_client, catalogue):
    assert len(names(api_client, "   ")) == len(catalogue)


def test_facet_counts_stay_true_while_searching(api_client, catalogue):
    data = api_client.get(FACETS, {"search": "gharara"}).json()

    assert data["total"] == 2
    assert sum(option["count"] for option in data["fabric"]) == 2
