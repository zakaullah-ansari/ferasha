"""Cancelling a placed order gives its reserved stock back."""

from __future__ import annotations

import pytest

from apps.orders.models import OrderStatus
from apps.orders.state_machine import IllegalTransition, transition_order

pytestmark = pytest.mark.django_db


def test_cancelling_a_placed_order_releases_its_stock(placed_order, variant):
    variant.refresh_from_db()
    assert variant.stock_quantity == 4  # one reserved at checkout

    transition_order(placed_order, OrderStatus.CANCELLED, reason="Customer changed mind")

    variant.refresh_from_db()
    assert variant.stock_quantity == 5


def test_stock_is_released_once_even_if_cancel_is_retried(placed_order, variant):
    transition_order(placed_order, OrderStatus.CANCELLED)

    with pytest.raises(IllegalTransition):
        transition_order(placed_order, OrderStatus.CANCELLED)

    variant.refresh_from_db()
    assert variant.stock_quantity == 5


def test_other_transitions_leave_stock_alone(placed_order, variant):
    transition_order(placed_order, OrderStatus.PAYMENT_CONFIRMED)

    variant.refresh_from_db()
    assert variant.stock_quantity == 4
