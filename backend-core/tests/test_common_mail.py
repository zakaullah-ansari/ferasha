"""Shared email helpers: Indian rupee formatting, and escaping what customers type."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.common.mail import format_inr, wrap
from apps.users.emails import send_email_verification
from tests.factories import make_user


@pytest.mark.parametrize(
    ("amount", "shown"),
    [
        ("0", "₹0"),
        ("150.00", "₹150"),
        ("2625.00", "₹2,625"),
        ("14160.00", "₹14,160"),
        ("189000.00", "₹1,89,000"),
        ("25000000.00", "₹2,50,00,000"),
        ("2624.50", "₹2,625"),
    ],
)
def test_rupees_use_indian_grouping(amount, shown):
    assert format_inr(Decimal(amount)) == shown


def test_the_wrapper_escapes_heading_and_link():
    html = wrap('Hi <b onclick="x">you</b>', "<p>body</p>", "Go", 'https://ferasha.com/?a="b"')

    assert "<b onclick" not in html and "&lt;b onclick" in html
    assert 'a="b"' not in html


@pytest.mark.django_db
def test_a_name_cannot_inject_markup_into_account_emails(mailoutbox):
    send_email_verification(make_user(full_name='<a href="https://evil.example">Mallory</a>'))

    assert 'href="https://evil.example"' not in mailoutbox[0].alternatives[0][0]
