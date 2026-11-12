"""Password-guessing and breached-password defences.

- Per-account lockout: the per-IP login throttle cannot stop a botnet
  trying one password per IP against one account; this does.
- Breached passwords: refused at registration, reset and change, using
  Have I Been Pwned's k-anonymity range API (only 5 hex chars of a SHA-1
  leave the server). Its seam, ``PwnedPasswordValidator._range``, is
  stubbed to "not breached" for the whole suite in conftest.
"""

from __future__ import annotations

import hashlib
import urllib.error

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.users.validators import PwnedPasswordValidator

User = get_user_model()

pytestmark = pytest.mark.django_db


def login(api_client, email="ayesha@example.com", password="wrong-password-1"):  # noqa: S107
    return api_client.post(
        reverse("users:token-obtain-pair"), {"email": email, "password": password}, format="json"
    )


def suffix_of(password: str) -> str:
    return hashlib.sha1(password.encode()).hexdigest().upper()[5:]  # noqa: S324 - HIBP's format


class TestAccountLockout:
    def test_locks_an_account_after_repeated_failures(self, api_client, customer, settings):
        settings.LOGIN_FAILURE_LIMIT = 3
        for _ in range(3):
            assert login(api_client).status_code == 401
        locked = login(api_client, password="Correct-Horse-9182")
        assert locked.status_code == 429
        assert "this account" in locked.data["detail"]

    def test_lockout_is_per_account_and_case_blind(self, api_client, customer, other_customer, settings):
        settings.LOGIN_FAILURE_LIMIT = 2
        login(api_client, email="AYESHA@example.com")
        login(api_client, email="ayesha@example.com ")
        assert login(api_client, password="Correct-Horse-9182").status_code == 429
        # Someone else's account is untouched.
        assert login(api_client, email="zainab@example.com", password="Correct-Horse-9182").status_code == 200

    def test_success_clears_the_count(self, api_client, customer, settings):
        settings.LOGIN_FAILURE_LIMIT = 2
        login(api_client)
        assert login(api_client, password="Correct-Horse-9182").status_code == 200
        assert login(api_client).status_code == 401  # count restarted, not locked

    def test_unknown_emails_lock_the_same_way(self, api_client, settings):
        """Otherwise the lockout itself would reveal which emails have accounts."""
        settings.LOGIN_FAILURE_LIMIT = 1
        login(api_client, email="nobody@example.com")
        assert login(api_client, email="nobody@example.com").status_code == 429


class TestPwnedPasswords:
    def test_refuses_a_breached_password(self, monkeypatch):
        breached = "Summer-2019-pass"
        body = f"0000000000000000000000000000000000A:0\n{suffix_of(breached)}:4120\n"
        monkeypatch.setattr(PwnedPasswordValidator, "_range", lambda self, prefix: body)
        with pytest.raises(ValidationError, match="data breach"):
            PwnedPasswordValidator().validate(breached)

    def test_padding_rows_with_zero_count_are_ignored(self, monkeypatch):
        password = "Quiet-Lantern-5521"
        monkeypatch.setattr(
            PwnedPasswordValidator, "_range", lambda self, prefix: f"{suffix_of(password)}:0\n"
        )
        PwnedPasswordValidator().validate(password)

    def test_only_the_hash_prefix_is_sent(self, monkeypatch):
        sent: list[str] = []

        def capture(self, prefix):
            sent.append(prefix)
            return ""

        monkeypatch.setattr(PwnedPasswordValidator, "_range", capture)
        PwnedPasswordValidator().validate("Correct-Horse-9182")
        assert sent == [hashlib.sha1(b"Correct-Horse-9182").hexdigest().upper()[:5]]  # noqa: S324

    def test_fails_open_when_the_service_is_down(self, monkeypatch):
        """A breach database outage must never stop people signing up."""

        def down(self, prefix):
            raise urllib.error.URLError("timed out")

        monkeypatch.setattr(PwnedPasswordValidator, "_range", down)
        PwnedPasswordValidator().validate("Correct-Horse-9182")

    def test_registration_reports_it_under_password(self, api_client, monkeypatch):
        password = "Summer-2019-pass"
        monkeypatch.setattr(
            PwnedPasswordValidator, "_range", lambda self, prefix: f"{suffix_of(password)}:12\n"
        )
        response = api_client.post(
            reverse("users:register"),
            {"email": "n@example.com", "full_name": "N", "password": password, "accept_terms": True},
            format="json",
        )
        assert response.status_code == 400
        assert "data breach" in response.data["password"][0]

    def test_can_be_switched_off(self, monkeypatch, settings):
        settings.PWNED_PASSWORDS_CHECK = False

        def explode(self, prefix):
            raise AssertionError("must not be called")

        monkeypatch.setattr(PwnedPasswordValidator, "_range", explode)
        PwnedPasswordValidator().validate("Correct-Horse-9182")


class TestSessionRevocation:
    def test_access_token_dies_the_moment_the_password_changes(self, api_client, customer):
        tokens = login(api_client, password="Correct-Horse-9182").data
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert api_client.get(reverse("users:current-user")).status_code == 200

        customer.set_password("Brand-New-Pass-77")
        customer.save()
        assert api_client.get(reverse("users:current-user")).status_code == 401

    def test_revoking_is_one_round_trip_however_many_sessions(self, api_client, customer, django_assert_max_num_queries):
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        from apps.users.serializers import revoke_all_refresh_tokens

        for _ in range(6):
            login(api_client, password="Correct-Horse-9182")
        with django_assert_max_num_queries(2):
            assert revoke_all_refresh_tokens(customer) == 6
        assert BlacklistedToken.objects.filter(token__user=customer).count() == 6
        # Idempotent: already-revoked sessions are not counted twice.
        assert revoke_all_refresh_tokens(customer) == 0
