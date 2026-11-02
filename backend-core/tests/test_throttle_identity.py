"""Which IP the throttles count against.

Browser traffic reaches Django through one hop we control (the Next.js
storefront), so DRF must trust exactly that hop's X-Forwarded-For entry. With
DRF's default the whole header is used, and a client could choose the address
its login attempts count against: unlimited guessing, or a victim lockout.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import AnonRateThrottle


def ident(forwarded_for: str | None = None, peer: str = "10.0.0.5") -> str:
    meta = {"REMOTE_ADDR": peer}
    if forwarded_for is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return AnonRateThrottle().get_ident(Request(APIRequestFactory().post("/", **meta)))


def test_spoofed_leading_entries_do_not_change_the_identity():
    assert ident("6.6.6.6, 203.0.113.7") == ident("1.1.1.1, 203.0.113.7") == "203.0.113.7"


def test_the_storefront_supplied_address_is_used():
    assert ident("203.0.113.7") == "203.0.113.7"


def test_a_request_without_the_header_falls_back_to_the_peer_address():
    assert ident() == "10.0.0.5"
