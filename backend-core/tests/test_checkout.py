"""Checkout: server-side pricing, exactly-once placement, all-or-nothing writes.

Fixture basket: one Rs.12,000 suit (HSN 6204), taxed at the 18% GST 2.0 slab.
  Mumbai (MH, home state): CGST 1080 + SGST 1080, free delivery -> 14,160.00
  Bengaluru (KA):          IGST 18% of (12,000 + 150 delivery)  -> 14,337.00
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.cart.models import Cart
from apps.checkout import services
from apps.orders.models import Order, OrderEvent, OrderStatus
from apps.users.models import Address
from tests.conftest import BENGALURU, MUMBAI

QUOTE = reverse("checkout:checkout-quote")
PLACE = reverse("checkout:checkout-place-order")


def place(client, body, key=None):
    return client.post(
        PLACE, body, format="json", HTTP_IDEMPOTENCY_KEY=key or f"test-{uuid.uuid4()}"
    )


@pytest.mark.django_db
class TestQuote:
    def test_intra_state_is_split_cgst_sgst_with_free_delivery(self, auth_client, filled_cart):
        response = auth_client.post(QUOTE, {"address": MUMBAI}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["subtotal"] == "12000.00"
        assert response.data["shipping_charge"] == "0.00"
        assert response.data["tax"]["cgst_total"] == "1080.00"
        assert response.data["tax"]["sgst_total"] == "1080.00"
        assert response.data["tax"]["igst_total"] == "0.00"
        assert response.data["grand_total"] == "14160.00"

    def test_inter_state_is_igst_and_taxes_delivery(self, auth_client, filled_cart):
        response = auth_client.post(QUOTE, {"address": BENGALURU}, format="json")

        assert response.data["shipping_charge"] == "150.00"
        assert response.data["tax"]["igst_total"] == "2187.00"
        assert response.data["grand_total"] == "14337.00"

    def test_international_delivery_is_refused_not_guessed(self, auth_client, filled_cart):
        address = {**MUMBAI, "country_code": "AE", "state_code": ""}
        response = auth_client.post(QUOTE, {"address": address}, format="json")

        assert response.status_code == 400

    def test_empty_bag_cannot_be_quoted(self, auth_client, customer):
        response = auth_client.post(QUOTE, {"address": MUMBAI}, format="json")

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({}, id="neither"),
            pytest.param({"address": MUMBAI, "address_id": str(uuid.uuid4())}, id="both"),
            pytest.param({"address": {**MUMBAI, "phone": "not-a-phone"}}, id="bad-phone"),
        ],
    )
    def test_address_must_be_exactly_one_valid_address(self, auth_client, filled_cart, body):
        assert auth_client.post(QUOTE, body, format="json").status_code == 400

    def test_quoting_has_no_side_effects(self, auth_client, filled_cart, variant):
        auth_client.post(QUOTE, {"address": MUMBAI}, format="json")

        variant.refresh_from_db()
        assert variant.stock_quantity == 5
        assert not Order.objects.exists()


@pytest.mark.django_db
class TestPlaceOrder:
    def test_places_a_complete_order(self, auth_client, customer, filled_cart, variant):
        response = place(auth_client, {"address": MUMBAI})

        assert response.status_code == 201, response.data
        order = Order.objects.get(order_number=response.data["order_number"])
        assert order.order_number.startswith("FER-")
        assert order.customer == customer
        assert order.status == OrderStatus.PLACED
        assert order.placed_at is not None
        assert order.grand_total == Decimal("14160.00")
        assert order.shipping_address["city"] == "Mumbai"

        [line] = order.lines.all()
        assert (line.sku, line.quantity, line.unit_price) == (variant.sku, 1, Decimal("12000"))
        assert line.hsn_code == "6204"
        assert line.modesty_snapshot["badges"], "modesty as sold must be frozen on the line"

        snapshot = order.tax_snapshot
        assert snapshot.tax_total == Decimal("2160.00")
        assert snapshot.grand_total == order.grand_total
        assert OrderEvent.objects.filter(order=order, to_status=OrderStatus.PLACED).exists()

        variant.refresh_from_db()
        assert variant.stock_quantity == 4
        filled_cart.refresh_from_db()
        assert filled_cart.is_active is False

    def test_client_supplied_money_fields_are_ignored(self, auth_client, filled_cart):
        """Regression: place-order used to trust shipping_cost and tax_quote from the body."""
        body = {
            "address": BENGALURU,
            "shipping_cost": "0",
            "tax_quote": {"total_tax": "0"},
            "grand_total": "1.00",
        }
        response = place(auth_client, body)

        assert response.status_code == 201
        assert response.data["grand_total"] == "14337.00"

    def test_free_delivery_order_is_accepted(self, auth_client, filled_cart):
        """Regression: a Rs.0 shipping charge was treated as 'missing' and refused."""
        assert place(auth_client, {"address": MUMBAI}).status_code == 201

    def test_saved_address_can_be_used(self, auth_client, customer, filled_cart):
        saved = Address.objects.create(user=customer, **{**BENGALURU, "line2": "Indiranagar"})
        response = place(auth_client, {"address_id": str(saved.pk)})

        assert response.status_code == 201
        assert response.data["shipping_address"]["line2"] == "Indiranagar"

    def test_another_customers_saved_address_is_not_found(
        self, auth_client, other_customer, filled_cart
    ):
        theirs = Address.objects.create(user=other_customer, **MUMBAI)

        response = place(auth_client, {"address_id": str(theirs.pk)})

        assert response.status_code == 400
        assert not Order.objects.exists()

    def test_price_change_since_quote_is_reported_not_charged(
        self, auth_client, filled_cart, variant
    ):
        response = place(auth_client, {"address": MUMBAI, "expected_grand_total": "14000.00"})

        assert response.status_code == 409
        assert response.data["quote"]["grand_total"] == "14160.00"
        assert not Order.objects.exists()
        variant.refresh_from_db()
        assert variant.stock_quantity == 5

    def test_stock_shortfall_leaves_everything_untouched(self, auth_client, filled_cart, variant):
        variant.stock_quantity = 0
        variant.save()

        response = place(auth_client, {"address": MUMBAI})

        assert response.status_code == 400
        assert not Order.objects.exists()
        filled_cart.refresh_from_db()
        assert filled_cart.is_active is True

    def test_failure_after_writes_rolls_back_everything(
        self, customer, filled_cart, variant, monkeypatch
    ):
        def explode(*args, **kwargs):
            raise RuntimeError("state machine unavailable")

        monkeypatch.setattr(services, "transition_order", explode)

        with pytest.raises(RuntimeError):
            services.place_order(customer, dict(MUMBAI))

        assert not Order.objects.exists()
        variant.refresh_from_db()
        assert variant.stock_quantity == 5
        assert Cart.objects.get(pk=filled_cart.pk).is_active is True

    def test_second_submission_finds_the_bag_already_checked_out(self, customer, filled_cart):
        services.place_order(customer, dict(MUMBAI))

        with pytest.raises(services.CheckoutError, match="empty"):
            services.place_order(customer, dict(MUMBAI))
        assert Order.objects.count() == 1


@pytest.mark.django_db
class TestPlaceOrderIdempotency:
    def test_key_is_required(self, auth_client, filled_cart):
        response = auth_client.post(PLACE, {"address": MUMBAI}, format="json")

        assert response.status_code == 400
        assert not Order.objects.exists()

    def test_replay_returns_the_same_order_once(self, auth_client, filled_cart):
        first = place(auth_client, {"address": MUMBAI}, key="order-attempt-0001")
        replay = place(auth_client, {"address": MUMBAI}, key="order-attempt-0001")

        assert first.status_code == replay.status_code == 201
        assert replay.data["order_number"] == first.data["order_number"]
        assert replay["Idempotent-Replayed"] == "true"
        assert Order.objects.count() == 1

    def test_reusing_a_key_with_a_different_body_is_rejected(self, auth_client, filled_cart):
        place(auth_client, {"address": MUMBAI}, key="order-attempt-0002")
        response = place(auth_client, {"address": BENGALURU}, key="order-attempt-0002")

        assert response.status_code == 422

    def test_a_refusal_is_not_replayed(self, auth_client, filled_cart):
        """After a 409 price change the customer re-quotes and retries the same key."""
        stale = place(
            auth_client,
            {"address": MUMBAI, "expected_grand_total": "1.00"},
            key="order-attempt-0003",
        )
        retry = place(
            auth_client,
            {"address": MUMBAI, "expected_grand_total": "14160.00"},
            key="order-attempt-0003",
        )

        assert stale.status_code == 409
        assert retry.status_code == 201

    def test_keys_are_scoped_per_customer(self, auth_client, other_client, filled_cart):
        """Regression: unscoped keys let one customer replay another's order response."""
        mine = place(auth_client, {"address": MUMBAI}, key="shared-key-0004")
        theirs = place(other_client, {"address": MUMBAI}, key="shared-key-0004")

        assert mine.status_code == 201
        assert theirs.status_code == 400, "their own (empty) bag, not my order"
        assert "order_number" not in theirs.data
