"""Email verification and password reset.

The assertions here are mostly *negative* security properties - single use,
expiry, no enumeration, session revocation. Those are the parts that silently
regress during a refactor, because the happy path keeps working either way.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.tokens import (
    TokenInvalid,
    make_email_verification_token,
    make_password_reset_token,
    read_email_verification_token,
    read_password_reset_token,
)

pytestmark = pytest.mark.django_db

User = get_user_model()

PASSWORD = "Correct-Horse-Battery-7"
NEW_PASSWORD = "Th3-Atelier-Stitches!"


@pytest.fixture(autouse=True)
def _clear_throttles():
    """Throttle state is process-global; a leak makes later tests 429."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="zainab@example.com", full_name="Zainab Qureshi", password=PASSWORD
    )


# --------------------------------------------------------------------------- #
# Token primitives
# --------------------------------------------------------------------------- #


class TestTokenPrimitives:
    def test_verification_token_round_trips(self, user):
        token = make_email_verification_token(user)
        assert read_email_verification_token(token, User).pk == user.pk

    def test_verification_token_is_single_use(self, user):
        token = make_email_verification_token(user)
        read_email_verification_token(token, User)

        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])

        with pytest.raises(TokenInvalid, match="already been used"):
            read_email_verification_token(token, User)

    def test_verification_token_dies_when_email_changes(self, user):
        token = make_email_verification_token(user)
        user.email = "someone.else@example.com"
        user.save(update_fields=["email"])
        with pytest.raises(TokenInvalid):
            read_email_verification_token(token, User)

    def test_tampered_token_is_rejected(self, user):
        token = make_email_verification_token(user)
        for mutated in (token[:-1] + ("A" if token[-1] != "A" else "B"), token + "x", "garbage"):
            with pytest.raises(TokenInvalid):
                read_email_verification_token(mutated, User)

    def test_expired_token_is_rejected(self, user, monkeypatch):
        token = make_email_verification_token(user)
        monkeypatch.setattr("apps.users.tokens.EMAIL_VERIFY_MAX_AGE", -1)
        with pytest.raises(TokenInvalid, match="expired"):
            read_email_verification_token(token, User)

    def test_salts_are_not_interchangeable(self, user):
        """A verification token must not be usable as a reset token."""
        verify = make_email_verification_token(user)
        with pytest.raises(TokenInvalid):
            read_password_reset_token(verify, User)

        reset = make_password_reset_token(user)
        with pytest.raises(TokenInvalid):
            read_email_verification_token(reset, User)

    def test_reset_token_dies_when_password_changes(self, user):
        token = make_password_reset_token(user)
        user.set_password("Some-Other-Password-9")
        user.save(update_fields=["password"])
        with pytest.raises(TokenInvalid, match="already been used"):
            read_password_reset_token(token, User)

    def test_token_for_deleted_user_is_rejected(self, user):
        token = make_password_reset_token(user)
        user.delete()
        with pytest.raises(TokenInvalid):
            read_password_reset_token(token, User)


# --------------------------------------------------------------------------- #
# Verification endpoints
# --------------------------------------------------------------------------- #


class TestEmailVerificationFlow:
    def test_registration_sends_verification_mail(self, client):
        mail.outbox.clear()
        response = client.post(
            reverse("users:register"),
            {
                "email": "new@example.com",
                "full_name": "Noor Fatima",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["user"]["email_verified"] is False
        assert len(mail.outbox) == 1
        assert "new@example.com" in mail.outbox[0].to

    def test_full_verification_round_trip(self, client, user):
        assert user.email_is_verified is False
        token = make_email_verification_token(user)

        response = client.post(
            reverse("users:email-verify-confirm"), {"token": token}, format="json"
        )
        assert response.status_code == 200
        assert response.data["user"]["email_verified"] is True

        user.refresh_from_db()
        assert user.email_verified_at is not None

    def test_confirm_rejects_replay(self, client, user):
        token = make_email_verification_token(user)
        assert client.post(
            reverse("users:email-verify-confirm"), {"token": token}, format="json"
        ).status_code == 200
        replay = client.post(
            reverse("users:email-verify-confirm"), {"token": token}, format="json"
        )
        assert replay.status_code == 400

    def test_request_is_neutral_for_unknown_address(self, client):
        mail.outbox.clear()
        response = client.post(
            reverse("users:email-verify-request"),
            {"email": "ghost@example.com"},
            format="json",
        )
        assert response.status_code == 202
        assert len(mail.outbox) == 0

    def test_request_response_is_identical_for_known_and_unknown(self, client, user):
        known = client.post(
            reverse("users:email-verify-request"), {"email": user.email}, format="json"
        )
        unknown = client.post(
            reverse("users:email-verify-request"), {"email": "ghost@example.com"}, format="json"
        )
        assert known.status_code == unknown.status_code == 202
        assert known.data == unknown.data

    def test_request_is_silent_for_already_verified_account(self, client, user):
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
        mail.outbox.clear()

        response = client.post(
            reverse("users:email-verify-request"), {"email": user.email}, format="json"
        )
        assert response.status_code == 202
        assert len(mail.outbox) == 0, "re-sending would leak verification state"


# --------------------------------------------------------------------------- #
# Password reset endpoints
# --------------------------------------------------------------------------- #


class TestPasswordResetFlow:
    def test_request_sends_mail_for_known_account(self, client, user):
        mail.outbox.clear()
        response = client.post(
            reverse("users:password-reset-request"), {"email": user.email}, format="json"
        )
        assert response.status_code == 202
        assert len(mail.outbox) == 1

    def test_request_is_neutral_for_unknown_account(self, client, user):
        mail.outbox.clear()
        known = client.post(
            reverse("users:password-reset-request"), {"email": user.email}, format="json"
        )
        mail.outbox.clear()
        unknown = client.post(
            reverse("users:password-reset-request"), {"email": "ghost@example.com"}, format="json"
        )
        assert known.data == unknown.data
        assert known.status_code == unknown.status_code == 202
        assert len(mail.outbox) == 0

    def test_request_ignores_deactivated_accounts(self, client, user):
        user.is_active = False
        user.save(update_fields=["is_active"])
        mail.outbox.clear()
        response = client.post(
            reverse("users:password-reset-request"), {"email": user.email}, format="json"
        )
        assert response.status_code == 202
        assert len(mail.outbox) == 0

    def test_confirm_changes_password(self, client, user):
        token = make_password_reset_token(user)
        response = client.post(
            reverse("users:password-reset-confirm"),
            {
                "token": token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert not user.check_password(PASSWORD)

    def test_confirm_verifies_the_email_as_a_side_effect(self, client, user):
        assert user.email_verified_at is None
        token = make_password_reset_token(user)
        client.post(
            reverse("users:password-reset-confirm"),
            {"token": token, "new_password": NEW_PASSWORD, "new_password_confirm": NEW_PASSWORD},
            format="json",
        )
        user.refresh_from_db()
        assert user.email_verified_at is not None, "reset proves mailbox control"

    def test_confirm_rejects_replay(self, client, user):
        token = make_password_reset_token(user)
        payload = {
            "token": token,
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        }
        assert client.post(
            reverse("users:password-reset-confirm"), payload, format="json"
        ).status_code == 200

        replay = client.post(
            reverse("users:password-reset-confirm"),
            {
                "token": token,
                "new_password": "Yet-Another-Pass-11",
                "new_password_confirm": "Yet-Another-Pass-11",
            },
            format="json",
        )
        assert replay.status_code == 400
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD), "replay must not overwrite the new password"

    def test_confirm_rejects_mismatched_confirmation(self, client, user):
        token = make_password_reset_token(user)
        response = client.post(
            reverse("users:password-reset-confirm"),
            {"token": token, "new_password": NEW_PASSWORD, "new_password_confirm": "different-1"},
            format="json",
        )
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_confirm_enforces_password_policy(self, client, user):
        token = make_password_reset_token(user)
        response = client.post(
            reverse("users:password-reset-confirm"),
            {"token": token, "new_password": "password12", "new_password_confirm": "password12"},
            format="json",
        )
        assert response.status_code == 400
        assert "new_password" in response.data

    def test_confirm_revokes_outstanding_refresh_tokens(self, client, user):
        login = client.post(
            reverse("users:token-obtain-pair"),
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        assert login.status_code == 200
        refresh = login.data["refresh"]

        # The stolen session works before the reset.
        assert client.post(
            reverse("users:token-refresh"), {"refresh": refresh}, format="json"
        ).status_code == 200

        token = make_password_reset_token(user)
        client.post(
            reverse("users:password-reset-confirm"),
            {"token": token, "new_password": NEW_PASSWORD, "new_password_confirm": NEW_PASSWORD},
            format="json",
        )

        after = client.post(reverse("users:token-refresh"), {"refresh": refresh}, format="json")
        assert after.status_code == 401, "reset must kill an attacker's existing session"


class TestPasswordChangeRevocation:
    def test_change_revokes_other_sessions_and_notifies(self, client, user):
        login = client.post(
            reverse("users:token-obtain-pair"),
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        refresh, access = login.data["refresh"], login.data["access"]

        mail.outbox.clear()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.post(
            reverse("users:password-change"),
            {
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 1, "a password change must be announced out of band"

        client.credentials()
        assert client.post(
            reverse("users:token-refresh"), {"refresh": refresh}, format="json"
        ).status_code == 401
