"""Sign in with an outside identity provider (OpenID Connect, code flow + PKCE).

The flow, end to end:

1. The storefront asks ``authorize()`` for a URL. A fresh ``state``, PKCE
   verifier and ``nonce`` come back with it; the storefront keeps them in a
   short-lived httpOnly cookie and sends the browser to the provider.
2. The provider returns the browser to the storefront's callback with a code.
   The storefront checks ``state`` against its cookie, then hands code,
   verifier and nonce to Django.
3. ``exchange()`` trades the code for an ID token, server to server, with the
   client secret (which never leaves Django), and validates the token.
4. ``sign_in()`` finds or creates the user under the linking policy below.

Adding a provider (Apple, Meta) is one ``OAuthProvider`` subclass registered
in ``PROVIDERS``; the views, storefront routes and buttons are generic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import SocialAccount, UserRole
from .serializers import revoke_all_refresh_tokens

logger = logging.getLogger(__name__)
User = get_user_model()


class SocialAuthError(Exception):
    """The provider's answer cannot be trusted or used. Safe to show the message."""

    status = 400


class SocialAuthForbidden(SocialAuthError):
    status = 403


class SocialAuthConflict(SocialAuthError):
    status = 409


@dataclass(frozen=True)
class SocialIdentity:
    provider: str
    subject: str
    email: str
    full_name: str
    #: True only when the provider runs the inbox itself (Gmail, a Workspace
    #: domain), so a verified address there proves the person owns it.
    email_authoritative: bool


@dataclass(frozen=True)
class AuthorizationRequest:
    authorization_url: str
    state: str
    code_verifier: str
    nonce: str


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def callback_url(provider_id: str) -> str:
    """Where the provider sends the browser back. From settings only, never the request."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/api/session/oauth/{provider_id}/callback"


class OAuthProvider(ABC):
    id: str
    name: str
    authorization_endpoint: str
    token_endpoint: str
    scopes: tuple[str, ...] = ("openid", "email", "profile")

    @property
    @abstractmethod
    def client_id(self) -> str: ...

    @property
    @abstractmethod
    def client_secret(self) -> str: ...

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorize(self) -> AuthorizationRequest:
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)  # 64 chars, inside RFC 7636's 43-128
        nonce = secrets.token_urlsafe(32)
        query = {
            "client_id": self.client_id,
            "redirect_uri": callback_url(self.id),
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
            **self.extra_authorize_params(),
        }
        url = f"{self.authorization_endpoint}?{urllib.parse.urlencode(query)}"
        return AuthorizationRequest(url, state, verifier, nonce)

    def extra_authorize_params(self) -> dict[str, str]:
        return {}

    def exchange(self, *, code: str, code_verifier: str, nonce: str) -> SocialIdentity:
        response = self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": callback_url(self.id),
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )
        token = response.get("id_token")
        if not isinstance(token, str):
            raise SocialAuthError(f"{self.name} did not return an identity.")
        return self.identity(self._claims(token), nonce)

    def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        """POST to the token endpoint. The single network seam (tests replace it)."""
        # The endpoint is a fixed https:// class constant, never caller input.
        request = urllib.request.Request(  # noqa: S310
            self.token_endpoint,
            data=urllib.parse.urlencode(form).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as reply:  # noqa: S310
                return json.loads(reply.read())
        except urllib.error.HTTPError as exc:
            # 400 here is a used, expired or forged code; worth a line, not an alert.
            logger.info("%s token exchange refused: %s", self.id, exc.code)
            raise SocialAuthError(f"{self.name} did not accept the sign-in. Please try again.") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logger.warning("%s token exchange failed: %s", self.id, exc)
            raise SocialAuthError(f"We couldn't reach {self.name}. Please try again.") from exc

    @staticmethod
    def _claims(token: str) -> dict[str, Any]:
        """The ID token's payload.

        The signature is not checked, deliberately: this token came straight
        from the provider's token endpoint over TLS, in exchange for a
        single-use code and our client secret, which OpenID Connect Core
        3.1.3.7 (6) accepts in place of signature validation. The claims are
        still checked in ``identity``.
        """
        try:
            payload = token.split(".")[1]
            return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        except (IndexError, ValueError) as exc:
            raise SocialAuthError("The sign-in response was malformed.") from exc

    @abstractmethod
    def identity(self, claims: dict[str, Any], nonce: str) -> SocialIdentity: ...


class GoogleProvider(OAuthProvider):
    id = "google"
    name = "Google"
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"  # noqa: S105 - a URL, not a secret
    issuers = frozenset({"https://accounts.google.com", "accounts.google.com"})
    #: Domains whose inboxes Google itself runs.
    google_mail_domains = frozenset({"gmail.com", "googlemail.com"})

    @property
    def client_id(self) -> str:
        return settings.GOOGLE_OAUTH_CLIENT_ID

    @property
    def client_secret(self) -> str:
        return settings.GOOGLE_OAUTH_CLIENT_SECRET

    def extra_authorize_params(self) -> dict[str, str]:
        # Always show the account chooser: shared family phones are common.
        return {"prompt": "select_account"}

    def identity(self, claims: dict[str, Any], nonce: str) -> SocialIdentity:
        invalid = SocialAuthError("The Google sign-in could not be verified. Please try again.")
        if claims.get("iss") not in self.issuers or claims.get("aud") != self.client_id:
            raise invalid
        exp = claims.get("exp")
        if not isinstance(exp, int | float) or exp <= time.time():
            raise invalid
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise invalid
        subject, email = claims.get("sub"), claims.get("email")
        if not isinstance(subject, str) or not subject or not isinstance(email, str) or "@" not in email:
            raise invalid
        if claims.get("email_verified") is not True:
            raise SocialAuthError("Please verify your email with Google first, then try again.")

        email = email.strip().lower()
        domain = email.rsplit("@", 1)[1]
        name = claims.get("name")
        return SocialIdentity(
            provider=self.id,
            subject=subject,
            email=email,
            full_name=" ".join(str(name).split()) if name else email.split("@", 1)[0],
            email_authoritative=domain in self.google_mail_domains or claims.get("hd") == domain,
        )


PROVIDERS: dict[str, OAuthProvider] = {provider.id: provider for provider in (GoogleProvider(),)}


def configured_provider(provider_id: str) -> OAuthProvider | None:
    provider = PROVIDERS.get(provider_id)
    return provider if provider and provider.is_configured else None


def configured_providers() -> list[OAuthProvider]:
    return [provider for provider in PROVIDERS.values() if provider.is_configured]


def sign_in(identity: SocialIdentity) -> tuple[Any, bool]:
    """The user this identity signs in as, and whether it was just created.

    Linking policy:
    - A known (provider, subject) signs in as its user.
    - Otherwise an existing account with the same email is linked only when
      the provider is authoritative for that address. If that account never
      verified its email, someone else may have registered it first ("pre-
      hijacking"): their password and sessions are revoked, so only the
      person who proved the inbox can get in.
    - Back-office accounts never sign in this way: they keep the password
      sign-in that guards the admin.
    - Otherwise a new verified customer is created, with no password (they
      can set one through "Forgot password").
    """
    try:
        return _sign_in(identity)
    except IntegrityError:
        # Two callbacks for the same new person raced; the other one won.
        return _sign_in(identity)


@transaction.atomic
def _sign_in(identity: SocialIdentity) -> tuple[Any, bool]:
    link = (
        SocialAccount.objects.select_related("user")
        .filter(provider=identity.provider, subject=identity.subject)
        .first()
    )
    if link:
        _check_allowed(link.user)
        link.last_used_at = timezone.now()
        link.save(update_fields=["last_used_at"])
        return link.user, False

    user = User.objects.filter(email__iexact=identity.email).first()
    created = user is None
    if user is not None:
        _check_allowed(user)
        if not identity.email_authoritative:
            raise SocialAuthConflict(
                "An account already uses this email. Please sign in with your password."
            )
        if not user.email_is_verified:
            user.set_unusable_password()
            user.email_verified_at = timezone.now()
            user.save(update_fields=["password", "email_verified_at", "updated_at"])
            revoke_all_refresh_tokens(user)
    else:
        now = timezone.now()
        user = User.objects.create_user(
            email=identity.email,
            password=None,
            full_name=identity.full_name[:180],
            role=UserRole.CUSTOMER,
            email_verified_at=now,
            # The storefront states the terms beside every sign-in button.
            accepted_terms_at=now,
        )
    SocialAccount.objects.create(
        user=user, provider=identity.provider, subject=identity.subject, email=identity.email
    )
    return user, created


def _check_allowed(user) -> None:
    if not user.is_active:
        raise SocialAuthForbidden("This account has been deactivated.")
    if user.is_back_office:
        raise SocialAuthForbidden("Staff accounts sign in with their password.")
