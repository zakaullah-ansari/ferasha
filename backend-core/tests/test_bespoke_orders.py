"""Ordering a bespoke piece through the bag, end to end.

The invariants: measurements are validated by the server (when the line is
added and again at checkout) and frozen onto the order; every bespoke piece
is its own line; the made-to-measure variant never holds or releases stock;
and the surcharge is charged, inside the garment's taxable value.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.cart import services as cart_services
from apps.catalog.enums import SizeStandard
from apps.orders.models import OrderStatus
from apps.orders.state_machine import transition_order
from tests.conftest import MUMBAI
from tests.factories import make_product, make_variant

pytestmark = pytest.mark.django_db

MERGE = reverse("cart:cart-merge")
QUOTE = reverse("checkout:checkout-quote")
PLACE = reverse("checkout:checkout-place-order")

#: A coherent suit in inches (REQUIRED_BY_GARMENT["suit_set"]).
SUIT = {"bust": 36, "waist": 30, "hip": 38, "shoulder": 14, "kameez_length": 42, "sleeve_length": 22}


@pytest.fixture
def bespoke_product():
    product = make_product(
        name="Chikankari Suit",
        supports_bespoke=True,
        bespoke_surcharge=Decimal("3000.00"),
        stitching_days=14,
    )
    make_variant(product=product, size=SizeStandard.M, stock_quantity=5, sku="CHK-M")
    custom = make_variant(product=product, size=SizeStandard.CUSTOM, stock_quantity=0, sku="CHK-CUSTOM")
    return product, custom


def bespoke_line(custom, measurements=None, **preferences):
    return {
        "variant_id": str(custom.pk),
        "quantity": 1,
        "bespoke": {"measurements": measurements or SUIT, "preferences": preferences},
    }


def merge(client, *items):
    return client.post(MERGE, {"items": list(items), "replace": True}, format="json")


def place(client):
    return client.post(PLACE, {"address": MUMBAI}, format="json", HTTP_IDEMPOTENCY_KEY=f"t-{uuid.uuid4()}")


class TestTheBag:
    def test_a_bespoke_line_is_accepted_though_the_variant_holds_no_stock(self, auth_client, bespoke_product):
        _, custom = bespoke_product

        response = merge(auth_client, bespoke_line(custom))

        assert response.status_code == 200, response.data
        assert response.data["skipped"] == []
        [line] = response.data["items"]
        assert line["is_bespoke"] is True and line["quantity"] == 1

    def test_two_bespoke_pieces_stay_two_lines(self, auth_client, bespoke_product):
        _, custom = bespoke_product
        sister = {**SUIT, "bust": 34, "waist": 28, "hip": 36}

        response = merge(auth_client, bespoke_line(custom), bespoke_line(custom, sister))

        assert [line["quantity"] for line in response.data["items"]] == [1, 1]

    def test_a_bespoke_line_is_always_one_piece(self, auth_client, bespoke_product):
        _, custom = bespoke_product

        response = merge(auth_client, {**bespoke_line(custom), "quantity": 3})

        assert response.data["items"][0]["quantity"] == 1

    def test_measurements_the_atelier_cannot_cut_from_are_refused_with_the_reason(self, auth_client, bespoke_product):
        _, custom = bespoke_product
        missing_hip = {k: v for k, v in SUIT.items() if k != "hip"}

        response = merge(auth_client, bespoke_line(custom, missing_hip))

        assert response.status_code == 400
        assert "hip" in str(response.data).lower()

    @pytest.mark.parametrize("case", ["not_bespoke_product", "not_custom_variant"])
    def test_only_a_made_to_measure_variant_of_a_bespoke_product(self, auth_client, bespoke_product, case):
        product, _ = bespoke_product
        if case == "not_bespoke_product":
            plain = make_product()
            variant = make_variant(product=plain, size=SizeStandard.CUSTOM, stock_quantity=0)
        else:
            variant = product.variants.get(size=SizeStandard.M)

        response = merge(auth_client, bespoke_line(variant))

        assert response.status_code == 400


class TestCheckout:
    def test_the_quote_charges_the_surcharge_in_the_taxable_value(self, auth_client, bespoke_product):
        _, custom = bespoke_product
        merge(auth_client, bespoke_line(custom))

        data = auth_client.post(QUOTE, {"address": MUMBAI}, format="json").data

        assert data["subtotal"] == "15000.00"  # 12,000 garment + 3,000 stitching
        [line] = data["lines"]
        assert (line["unit_price"], line["line_total"], line["is_bespoke"]) == ("15000.00", "15000.00", True)
        assert line["variant_label"].startswith("Made to measure")
        assert Decimal(data["tax_total"]) == Decimal("2700.00")  # 18% of 15,000, as one composite supply

    def test_placing_freezes_the_measurements_onto_the_order(self, auth_client, bespoke_product):
        product, custom = bespoke_product
        merge(auth_client, bespoke_line(custom, lining_preference="full"))

        response = place(auth_client)

        assert response.status_code == 201, response.data
        from apps.orders.models import Order

        order = Order.objects.get(order_number=response.data["order_number"])
        line = order.lines.get()
        assert line.is_bespoke is True
        assert line.unit_price == Decimal("15000.00")
        assert line.variant_label.startswith("Made to measure")
        spec = line.tailoring_spec
        assert spec.measurements == {k: float(v) for k, v in SUIT.items()}
        assert spec.preferences == {"lining_preference": "full"}
        assert (spec.unit_system, spec.garment_type, spec.surcharge) == ("inch", product.garment_type, Decimal("3000.00"))

    def test_made_to_measure_never_touches_stock(self, auth_client, bespoke_product):
        _, custom = bespoke_product
        merge(auth_client, bespoke_line(custom))
        response = place(auth_client)
        from apps.orders.models import Order

        order = Order.objects.get(order_number=response.data["order_number"])
        transition_order(order, OrderStatus.CANCELLED)

        custom.refresh_from_db()
        assert custom.stock_quantity == 0  # not reserved, and not "released" into sale on cancel

    def test_a_mixed_bag_reserves_only_the_ready_made_piece(self, auth_client, bespoke_product):
        product, custom = bespoke_product
        ready = product.variants.get(size=SizeStandard.M)
        merge(auth_client, {"variant_id": str(ready.pk), "quantity": 2}, bespoke_line(custom))

        assert place(auth_client).status_code == 201

        ready.refresh_from_db()
        custom.refresh_from_db()
        assert (ready.stock_quantity, custom.stock_quantity) == (3, 0)

    def test_measurements_are_checked_again_at_checkout(self, auth_client, customer, bespoke_product):
        """A line that slipped in unchecked (an older client, a direct write) still cannot be ordered."""
        _, custom = bespoke_product
        cart = cart_services.get_active_cart(customer)
        cart.items.create(variant=custom, quantity=1, is_bespoke=True, measurements={"bust": 36})

        response = place(auth_client)

        assert response.status_code == 400
