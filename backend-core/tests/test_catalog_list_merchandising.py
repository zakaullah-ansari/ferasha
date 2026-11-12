"""The product list carries what a listing card needs to merchandise a piece:
the struck-through price for a sale label and the listing date for "New"."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

PRODUCTS = reverse("catalog:product-list")


def test_list_exposes_listing_date_and_compare_at_price(api_client):
    product = make_product(base_price=Decimal("8000.00"), compare_at_price=Decimal("10000.00"))
    make_variant(product=product)

    item = api_client.get(PRODUCTS).json()["results"][0]

    assert parse_datetime(item["created_at"]) == product.created_at
    assert item["compare_at_price"] == "10000.00"
