"""Authentication for the AI engine.

Two distinct mechanisms, deliberately not shared:

* **Inbound** - callers present a Django-issued HS256 JWT. The engine only
  ever *verifies*; it never mints tokens. Compromising the engine must not
  yield the ability to forge a customer session.

* **Outbound** - worker callbacks to Django are signed with HMAC-SHA256 over
  a canonical payload, plus a timestamp and a single-use nonce. Knowing an
  asset ID must not be enough to mark it APPROVED, or the entire privacy
  pipeline can be bypassed with one forged HTTP request.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class Principal:
    """The authenticated caller, as described by the Django-issued token."""

    __slots__ = ("user_id", "email", "role", "is_back_office", "email_verified")

    def __init__(self, claims: dict[str, Any]) -> None:
        self.user_id: str = str(claims.get("user_id", ""))
        self.email: str = claims.get("email", "")
        self.role: str = claims.get("role", "")
        self.is_back_office: bool = bool(claims.get("is_back_office", False))
        self.email_verified: bool = bool(claims.get("email_verified", False))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Principal {self.email or self.user_id} role={self.role}>"


def verify_token(token: str) -> Principal:
    """Decode and validate a Django-issued access token."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_signing_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        ) from exc

    if claims.get("token_type") == "refresh":
        # A refresh token must never be accepted as an access credential.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A refresh token cannot be used to authenticate a request.",
        )

    return Principal(claims)


async def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


async def require_back_office(
    principal: Principal = Depends(require_principal),
) -> Principal:
    if not principal.is_back_office:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Back-office role required.",
        )
    return principal


# --------------------------------------------------------------------------- #
# HMAC callback signing
# --------------------------------------------------------------------------- #


def canonical_payload(body: dict[str, Any]) -> bytes:
    """Deterministic byte encoding of a payload.

    Sorted keys and no incidental whitespace, so that signer and verifier
    always agree regardless of dict ordering or JSON library defaults.
    """
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_callback(body: dict[str, Any]) -> dict[str, str]:
    """Produce the signature headers for a worker -> Django callback."""
    settings = get_settings()
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex

    message = b".".join([timestamp.encode(), nonce.encode(), canonical_payload(body)])
    signature = hmac.new(
        settings.ai_engine_shared_secret.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()

    return {
        "X-Ferasha-Timestamp": timestamp,
        "X-Ferasha-Nonce": nonce,
        "X-Ferasha-Signature": signature,
    }


def verify_callback_signature(
    body: dict[str, Any],
    timestamp: str,
    nonce: str,
    signature: str,
    *,
    seen_nonces: set[str] | None = None,
) -> None:
    """Verify a signed callback. Raises HTTPException on any failure.

    Django implements the same check on its inbound endpoint; this
    implementation is shared via tests to guarantee the two agree.
    """
    settings = get_settings()

    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Malformed timestamp.") from exc

    skew = abs(int(time.time()) - sent_at)
    if skew > settings.callback_max_skew_seconds:
        raise HTTPException(status_code=401, detail="Callback timestamp outside accepted window.")

    if seen_nonces is not None:
        if nonce in seen_nonces:
            raise HTTPException(status_code=401, detail="Callback nonce already used.")
        seen_nonces.add(nonce)

    message = b".".join([timestamp.encode(), nonce.encode(), canonical_payload(body)])
    expected = hmac.new(
        settings.ai_engine_shared_secret.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()

    # compare_digest, not ==, to avoid leaking the signature byte by byte.
    if not hmac.compare_digest(expected, signature or ""):
        raise HTTPException(status_code=401, detail="Invalid callback signature.")


async def enforce_body_limit(request: Request) -> None:
    """Reject oversized bodies before they are buffered into memory."""
    settings = get_settings()
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="Upload too large.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Malformed Content-Length.") from exc
