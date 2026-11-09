"""Customers hear about their order at the moments that matter, and only then.

Sent after the change commits (a rolled-back move emails nobody), never
raising into the move itself, and with every customer-supplied value escaped.
"""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

import pytest

from apps.orders.models import Order, OrderLine, OrderStatus
from apps.orders.state_machine import transition_order
from tests.factories import make_user

pytestmark = pytest.mark.django_db

S = OrderStatus


def make_order(status=S.PLACED, *, bespoke=False, product_name="Velvet Gharara - Emerald", **kw) -> Order:
    order = Order.objects.create(
        order_number=f"FER-{Order.objects.count() + 1:06d}",
        status=status,
        grand_total=Decimal("14160.00"),
        **{"guest_email": "guest@example.com", **kw},
    )
    OrderLine.objects.create(
        order=order,
        sku="VG-EM-M",
        product_name=product_name,
        variant_label="M / Emerald",
        hsn_code="6204",
        quantity=1,
        unit_price=Decimal("12000.00"),
        is_bespoke=bespoke,
    )
    return order


def move(order, *statuses, capture):
    for status in statuses:
        with capture(execute=True):
            transition_order(order, status)


def test_a_confirmed_order_tells_the_customer(django_capture_on_commit_callbacks, mailoutbox):
    ayesha = make_user(full_name="Ayesha Khan", email="ayesha@example.com")
    order = make_order(customer=ayesha, guest_email="")

    move(order, S.PAYMENT_CONFIRMED, capture=django_capture_on_commit_callbacks)

    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert mail.to == ["ayesha@example.com"]
    assert order.order_number in mail.subject
    assert "Velvet Gharara - Emerald" in mail.body
    assert f"/orders/{order.order_number}" in mail.body
    html = mail.alternatives[0][0]
    assert "Ayesha" in html and "₹14,160" in html


def test_guests_are_emailed_at_their_address(django_capture_on_commit_callbacks, mailoutbox):
    move(make_order(), S.PAYMENT_CONFIRMED, capture=django_capture_on_commit_callbacks)

    assert mailoutbox[0].to == ["guest@example.com"]


def test_quiet_steps_send_nothing(django_capture_on_commit_callbacks, mailoutbox):
    order = make_order(S.PAYMENT_CONFIRMED)

    move(order, S.IN_ATELIER, S.STITCHING, S.QUALITY_CHECK, S.PACKED, capture=django_capture_on_commit_callbacks)

    assert mailoutbox == []  # ready-made: no stitching news to give


def test_bespoke_customers_hear_when_stitching_starts(django_capture_on_commit_callbacks, mailoutbox):
    order = make_order(S.IN_ATELIER, bespoke=True)

    move(order, S.STITCHING, capture=django_capture_on_commit_callbacks)

    assert len(mailoutbox) == 1
    assert "stitch" in mailoutbox[0].subject.lower()


def test_shipped_and_delivered(django_capture_on_commit_callbacks, mailoutbox):
    order = make_order(S.PACKED)

    move(order, S.SHIPPED, S.DELIVERED, capture=django_capture_on_commit_callbacks)

    assert [("shipped" in m.subject.lower(), "delivered" in m.subject.lower()) for m in mailoutbox] == [
        (True, False),
        (False, True),
    ]


def test_an_unpaid_order_expiring_sends_nothing(django_capture_on_commit_callbacks, mailoutbox):
    move(make_order(S.PLACED), S.CANCELLED, capture=django_capture_on_commit_callbacks)

    assert mailoutbox == []


def test_cancelling_a_paid_order_mentions_the_refund(django_capture_on_commit_callbacks, mailoutbox):
    move(make_order(S.PAYMENT_CONFIRMED), S.CANCELLED, capture=django_capture_on_commit_callbacks)

    assert len(mailoutbox) == 1
    assert "refund" in mailoutbox[0].body.lower()


def test_customer_supplied_text_is_escaped(django_capture_on_commit_callbacks, mailoutbox):
    mallory = make_user(full_name='<a href="https://evil.example">Mallory</a>')
    order = make_order(customer=mallory, guest_email="", product_name="<script>x</script> Suit")

    move(order, S.PAYMENT_CONFIRMED, capture=django_capture_on_commit_callbacks)

    html = mailoutbox[0].alternatives[0][0]
    assert "<script>" not in html and 'href="https://evil.example"' not in html
    assert "&lt;script&gt;" in html


def test_a_mail_outage_never_blocks_the_order(django_capture_on_commit_callbacks):
    order = make_order()
    with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp down")):
        move(order, S.PAYMENT_CONFIRMED, capture=django_capture_on_commit_callbacks)

    order.refresh_from_db()
    assert order.status == S.PAYMENT_CONFIRMED


def test_nothing_is_sent_if_the_move_rolls_back(mailoutbox):
    from django.db import transaction

    order = make_order()
    with pytest.raises(RuntimeError), transaction.atomic():
        transition_order(order, S.PAYMENT_CONFIRMED)
        raise RuntimeError("something later in the same transaction failed")

    assert mailoutbox == []
