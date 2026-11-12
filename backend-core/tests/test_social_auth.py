"""Sign in with Google: provider discovery, the authorize step and account linking.

Google itself is never called: ``GoogleProvider._token_request`` is the one
network seam and every test replaces it with a canned token response.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.users.models import SocialAccount, UserRole
from apps.users.social import GoogleProvider, SocialAuthError

User = get_user_model()

pytestmark = pytest.mark.django_db

CLIENT_ID = "test-client.apps.googleusercontent.com"


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def id_token(**overrides) -> str:
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "google-sub-1",
        "email": "ayesha@gmail.com",
        "email_verified": True,
        "name": "Ayesha Khan",
        "nonce": "n0nce",
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    claims = {key: value for key, value in claims.items() if value is not None}
    return f"{_b64({'alg': 'RS256'})}.{_b64(claims)}.signature"


@pytest.fixture(autouse=True)
def google_configured(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = CLIENT_ID
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "test-secret"
    settings.FRONTEND_BASE_URL = "https://shop.example"


@pytest.fixture
def google_returns(monkeypatch):
    """Make Google's token endpoint answer with an id_token carrying ``claims``."""

    def install(**claims):
        token = id_token(**claims)
        monkeypatch.setattr(GoogleProvider, "_token_request", lambda self, form: {"id_token": token})

    return install


def callback(api_client, **body):
    payload = {"code": "auth-code", "code_verifier": "v" * 43, "nonce": "n0nce", **body}
    return api_client.post(
        reverse("users:social-callback", args=["google"]), payload, format="json"
    )


class TestProviders:
    def test_lists_google_when_configured(self, api_client):
        response = api_client.get(reverse("users:social-providers"))
        assert response.status_code == 200
        assert response.data == {"providers": [{"id": "google", "name": "Google"}]}

    def test_lists_nothing_without_keys(self, api_client, settings):
        settings.GOOGLE_OAUTH_CLIENT_ID = ""
        response = api_client.get(reverse("users:social-providers"))
        assert response.data == {"providers": []}

    def test_unconfigured_provider_cannot_start(self, api_client, settings):
        settings.GOOGLE_OAUTH_CLIENT_SECRET = ""
        response = api_client.post(reverse("users:social-authorize", args=["google"]))
        assert response.status_code == 404

    def test_unknown_provider_is_404(self, api_client):
        response = api_client.post(reverse("users:social-authorize", args=["myspace"]))
        assert response.status_code == 404


class TestAuthorize:
    def test_builds_a_pkce_url_for_our_own_callback(self, api_client):
        response = api_client.post(reverse("users:social-authorize", args=["google"]))
        assert response.status_code == 200
        data = response.data
        url = urlparse(data["authorization_url"])
        query = {key: values[0] for key, values in parse_qs(url.query).items()}

        assert url.netloc == "accounts.google.com"
        assert query["client_id"] == CLIENT_ID
        # Built from settings, never from the request: no open redirect.
        assert query["redirect_uri"] == "https://shop.example/api/session/oauth/google/callback"
        assert query["response_type"] == "code"
        assert query["scope"] == "openid email profile"
        assert query["state"] == data["state"]
        assert query["nonce"] == data["nonce"]
        assert query["code_challenge_method"] == "S256"
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert query["code_challenge"] == expected

    def test_every_start_is_fresh(self, api_client):
        url = reverse("users:social-authorize", args=["google"])
        first = api_client.post(url).data
        second = api_client.post(url).data
        assert first["state"] != second["state"]
        assert first["code_verifier"] != second["code_verifier"]


class TestNewAccounts:
    def test_creates_a_verified_customer_with_no_password(self, api_client, google_returns):
        google_returns()
        response = callback(api_client)
        assert response.status_code == 200, response.data
        assert response.data["created"] is True
        assert "access" in response.data and "refresh" in response.data

        user = User.objects.get(email="ayesha@gmail.com")
        assert user.full_name == "Ayesha Khan"
        assert user.role == UserRole.CUSTOMER
        assert user.email_is_verified
        assert user.accepted_terms_at is not None
        assert not user.has_usable_password()
        assert SocialAccount.objects.filter(user=user, provider="google", subject="google-sub-1").exists()

    def test_falls_back_to_the_email_name(self, api_client, google_returns):
        google_returns(name=None)
        callback(api_client)
        assert User.objects.get(email="ayesha@gmail.com").full_name == "ayesha"

    def test_returning_user_is_found_by_subject_not_email(self, api_client, google_returns):
        google_returns()
        callback(api_client)
        # They changed their Google email since; same Google account.
        google_returns(email="ayesha.k@gmail.com")
        response = callback(api_client)
        assert response.data["created"] is False
        assert User.objects.count() == 1


class TestLinkingExistingAccounts:
    def test_links_when_google_is_authoritative(self, api_client, google_returns):
        existing = User.objects.create_user(
            email="ayesha@gmail.com", password="Correct-Horse-9182", full_name="Ayesha"
        )
        existing.email_verified_at = timezone.now()
        existing.save()
        google_returns()
        response = callback(api_client)
        assert response.status_code == 200
        assert response.data["created"] is False
        existing.refresh_from_db()
        # Verified owner keeps their password.
        assert existing.check_password("Correct-Horse-9182")
        assert existing.social_accounts.get().subject == "google-sub-1"

    def test_pre_hijacked_account_loses_the_squatters_password(self, api_client, google_returns):
        """Someone registered this Gmail address first and never verified it."""
        squatted = User.objects.create_user(
            email="ayesha@gmail.com", password="Squatter-Pass-1234", full_name="Squatter"
        )
        google_returns()
        response = callback(api_client)
        assert response.status_code == 200
        squatted.refresh_from_db()
        assert not squatted.has_usable_password()
        assert squatted.email_is_verified

    def test_workspace_domain_is_authoritative(self, api_client, google_returns):
        User.objects.create_user(email="ayesha@kausar.in", password="Correct-Horse-9182", full_name="A")
        google_returns(email="ayesha@kausar.in", hd="kausar.in")
        assert callback(api_client).status_code == 200

    def test_refuses_to_link_where_google_is_not_authoritative(self, api_client, google_returns):
        """A Google account made with a Yahoo address proves nothing about that inbox."""
        User.objects.create_user(email="ayesha@yahoo.com", password="Correct-Horse-9182", full_name="A")
        google_returns(email="ayesha@yahoo.com")
        response = callback(api_client)
        assert response.status_code == 409
        assert not SocialAccount.objects.exists()

    def test_back_office_accounts_keep_password_sign_in(self, api_client, google_returns):
        User.objects.create_user(
            email="owner@gmail.com", password="Correct-Horse-9182", full_name="O", role=UserRole.ADMIN
        )
        google_returns(email="owner@gmail.com")
        assert callback(api_client).status_code == 403
        assert not SocialAccount.objects.exists()

    def test_deactivated_account_is_refused(self, api_client, google_returns):
        User.objects.create_user(
            email="ayesha@gmail.com", password="Correct-Horse-9182", full_name="A", is_active=False
        )
        google_returns()
        assert callback(api_client).status_code == 403


class TestTokenValidation:
    @pytest.mark.parametrize(
        "claims",
        [
            {"aud": "someone-elses-client"},
            {"iss": "https://evil.example"},
            {"nonce": "replayed"},
            {"exp": int(time.time()) - 10},
            {"email_verified": False},
            {"sub": None},
            {"email": None},
        ],
        ids=["audience", "issuer", "nonce", "expired", "unverified-email", "no-subject", "no-email"],
    )
    def test_rejects_bad_tokens(self, api_client, google_returns, claims):
        google_returns(**claims)
        response = callback(api_client)
        assert response.status_code == 400
        assert not User.objects.exists()

    def test_google_refusing_the_code_is_a_clean_400(self, api_client, monkeypatch):
        def refuse(self, form):
            raise SocialAuthError("Google did not accept the sign-in.")

        monkeypatch.setattr(GoogleProvider, "_token_request", refuse)
        response = callback(api_client)
        assert response.status_code == 400

    def test_requires_code_verifier_and_nonce(self, api_client):
        response = api_client.post(
            reverse("users:social-callback", args=["google"]), {"code": "x"}, format="json"
        )
        assert response.status_code == 400


class TestRegistrationWithoutConfirm:
    """The storefront shows the password instead of asking for it twice."""

    def test_confirm_is_optional(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "new@example.com",
                "full_name": "New",
                "password": "Correct-Horse-9182",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
