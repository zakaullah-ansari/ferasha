"""A customer's order history says what was bought, not just a number."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.cart import services as cart_services
from apps.checkout import services as checkout_services
from tests.conftest import MUMBAI
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

ORDERS = reverse("orders:order-list")


def test_each_order_names_what_was_bought(auth_client, placed_order):
    row = auth_client.get(ORDERS).json()["results"][0]

    assert row["order_number"] == placed_order.order_number
    assert row["item_summary"] == placed_order.lines.get().product_name


def test_several_garments_are_summed_up(auth_client, customer, variant):
    cart = cart_services.get_active_cart(customer)
    cart_services.add_item(cart, variant.pk, 1)
    for name in ("Velvet Gharara", "Raw Silk Blouse"):
        cart_services.add_item(cart, make_variant(product=make_product(name=name)).pk, 1)
    checkout_services.place_order(customer, dict(MUMBAI))

    summary = auth_client.get(ORDERS).json()["results"][0]["item_summary"]

    assert summary.endswith(" and 2 more")


def test_mine_means_mine_even_for_the_back_office(staff_user, placed_order):
    """Staff also shop: their own account page must not list every customer's orders."""
    from tests.conftest import _client_for

    staff = _client_for(staff_user)

    assert staff.get(ORDERS).json()["count"] == 1  # the back office sees everyone's
    assert staff.get(ORDERS, {"mine": "true"}).json()["count"] == 0  # but none are theirs


def test_mine_for_a_customer_is_their_own(auth_client, placed_order):
    assert auth_client.get(ORDERS, {"mine": "true"}).json()["count"] == 1
