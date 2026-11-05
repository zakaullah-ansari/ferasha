"""Unpaid orders give their stock back.

Placing an order reserves its stock. An order that is never paid must not
keep it: a few abandoned checkouts would otherwise show real pieces as sold
out until someone noticed.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.orders.models import OrderStatus
from apps.orders.services import expire_unpaid_orders
from apps.orders.state_machine import transition_order

pytestmark = pytest.mark.django_db

S = OrderStatus


def age(order, minutes: int):
    order.placed_at = timezone.now() - timedelta(minutes=minutes)
    order.save(update_fields=["placed_at"])
    return order


def test_an_unpaid_order_past_the_window_is_cancelled_and_its_stock_returned(placed_order, variant, settings):
    settings.UNPAID_ORDER_TTL_MINUTES = 30
    variant.refresh_from_db()
    held = variant.stock_quantity  # 4 of 5: one is reserved by the order
    age(placed_order, 31)

    assert expire_unpaid_orders() == [placed_order.order_number]

    placed_order.refresh_from_db()
    variant.refresh_from_db()
    assert placed_order.status == S.CANCELLED
    assert variant.stock_quantity == held + 1
    event = placed_order.events.get(to_status=S.CANCELLED)
    assert event.actor is None
    assert "not paid within 30 minutes" in event.reason


def test_an_order_inside_the_window_is_left_alone(placed_order, settings):
    settings.UNPAID_ORDER_TTL_MINUTES = 30
    age(placed_order, 29)

    assert expire_unpaid_orders() == []
    placed_order.refresh_from_db()
    assert placed_order.status == S.PLACED


def test_a_paid_order_is_never_touched(placed_order, settings):
    settings.UNPAID_ORDER_TTL_MINUTES = 30
    transition_order(placed_order, S.PAYMENT_CONFIRMED)
    age(placed_order, 600)

    assert expire_unpaid_orders() == []


def test_running_twice_is_harmless(placed_order, variant, settings):
    settings.UNPAID_ORDER_TTL_MINUTES = 30
    age(placed_order, 120)
    expire_unpaid_orders()
    variant.refresh_from_db()
    after_first = variant.stock_quantity

    assert expire_unpaid_orders() == []
    variant.refresh_from_db()
    assert variant.stock_quantity == after_first  # stock is not released twice


def test_the_command_reports_what_it_did(placed_order, settings):
    settings.UNPAID_ORDER_TTL_MINUTES = 30
    age(placed_order, 45)
    out = StringIO()

    call_command("expire_unpaid_orders", stdout=out)

    assert f"Cancelled 1 unpaid order: {placed_order.order_number}" in out.getvalue()
