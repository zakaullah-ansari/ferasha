"""Cart API: one bag per customer, never holding what checkout would refuse."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.cart.models import Cart
from apps.cart.services import MAX_QUANTITY_PER_LINE
from apps.catalog.enums import ProductStatus
from tests.factories import make_product, make_variant

CART = reverse("cart:cart-list")
SET_QUANTITY = reverse("cart:cart-set-quantity")
MERGE = reverse("cart:cart-merge")


@pytest.mark.django_db
class TestCartApi:
    def test_requires_authentication(self, api_client):
        assert api_client.get(CART).status_code == 401

    def test_empty_bag_is_created_on_first_read(self, auth_client, customer):
        response = auth_client.get(CART)

        assert response.status_code == 200
        assert response.data["items"] == []
        assert response.data["subtotal"] == "0.00"
        assert Cart.objects.filter(user=customer, is_active=True).count() == 1

    def test_add_prices_from_the_catalogue(self, auth_client, variant):
        response = auth_client.post(CART, {"variant_id": str(variant.pk), "quantity": 2})

        assert response.status_code == 201
        [line] = response.data["items"]
        assert line["sku"] == variant.sku
        assert line["unit_price"] == "12000.00"
        assert line["line_total"] == "24000.00"
        assert response.data["total_items"] == 2
        assert response.data["subtotal"] == "24000.00"

    def test_adding_twice_accumulates_on_one_line(self, auth_client, variant):
        auth_client.post(CART, {"variant_id": str(variant.pk), "quantity": 1})
        response = auth_client.post(CART, {"variant_id": str(variant.pk), "quantity": 2})

        assert len(response.data["items"]) == 1
        assert response.data["items"][0]["quantity"] == 3

    def test_quantity_is_clamped_to_stock(self, auth_client, variant):
        response = auth_client.post(CART, {"variant_id": str(variant.pk), "quantity": 9})

        assert response.data["items"][0]["quantity"] == variant.stock_quantity

    def test_quantity_is_clamped_to_the_per_line_cap(self, auth_client):
        plentiful = make_variant(stock_quantity=100)
        response = auth_client.post(CART, {"variant_id": str(plentiful.pk), "quantity": 50})

        assert response.data["items"][0]["quantity"] == MAX_QUANTITY_PER_LINE

    @pytest.mark.parametrize(
        "make",
        [
            pytest.param(lambda: make_variant(stock_quantity=0), id="out-of-stock"),
            pytest.param(lambda: make_variant(is_active=False), id="inactive-variant"),
            pytest.param(
                lambda: make_variant(product=make_product(status=ProductStatus.DRAFT)),
                id="unpublished-product",
            ),
        ],
    )
    def test_unpurchasable_items_are_refused(self, auth_client, make):
        response = auth_client.post(CART, {"variant_id": str(make().pk)})

        assert response.status_code == 400

    def test_unknown_variant_is_a_400_not_a_500(self, auth_client):
        response = auth_client.post(
            CART, {"variant_id": "00000000-0000-0000-0000-000000000000"}
        )

        assert response.status_code == 400

    def test_set_quantity_zero_removes_the_line(self, auth_client, variant):
        auth_client.post(CART, {"variant_id": str(variant.pk)})
        response = auth_client.post(
            SET_QUANTITY, {"variant_id": str(variant.pk), "quantity": 0}
        )

        assert response.status_code == 200
        assert response.data["items"] == []

    def test_remove_item(self, auth_client, variant):
        auth_client.post(CART, {"variant_id": str(variant.pk)})
        url = reverse("cart:cart-remove-item", kwargs={"variant_id": str(variant.pk)})

        assert auth_client.delete(url).data["items"] == []
        assert auth_client.delete(url).status_code == 404

    def test_merge_keeps_what_it_can_and_reports_the_rest(self, auth_client, variant):
        sold_out = make_variant(stock_quantity=0)
        response = auth_client.post(
            MERGE,
            {
                "items": [
                    {"variant_id": str(variant.pk), "quantity": 1},
                    {"variant_id": str(sold_out.pk), "quantity": 1},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert [line["sku"] for line in response.data["items"]] == [variant.sku]
        assert response.data["skipped"] == [str(sold_out.pk)]

    def test_customers_cannot_see_each_others_bags(self, auth_client, other_client, variant):
        auth_client.post(CART, {"variant_id": str(variant.pk)})

        assert other_client.get(CART).data["items"] == []

    def test_replace_makes_the_server_bag_exactly_the_client_bag(self, auth_client, variant):
        leftover = make_variant(stock_quantity=3)
        auth_client.post(CART, {"variant_id": str(leftover.pk)})

        response = auth_client.post(
            MERGE,
            {"items": [{"variant_id": str(variant.pk), "quantity": 2}], "replace": True},
            format="json",
        )

        assert [(line["sku"], line["quantity"]) for line in response.data["items"]] == [
            (variant.sku, 2)
        ]
