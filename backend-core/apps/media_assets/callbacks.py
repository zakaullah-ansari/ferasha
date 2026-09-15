"""HMAC verification for AI-engine callbacks.

This is the one route by which an asset can become APPROVED, so it is the
route an attacker would target. Knowing an asset ID must not be sufficient:
without the shared secret, a forged callback cannot mark an unblurred face
publishable.

The scheme mirrors ``ai-engine/app/core/security.py`` exactly. Both sides are
exercised against the same vectors in ``tests/test_media_callbacks.py`` so
they cannot drift apart silently.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed, ValidationError

logger = logging.getLogger(__name__)

#: Nonces are remembered for slightly longer than the accepted clock skew, so
#: a replay can never slip through the gap between expiry and the window.
NONCE_TTL_SECONDS = 900
MAX_SKEW_SECONDS = 300


def canonical_payload(body: dict[str, Any]) -> bytes:
    """Deterministic encoding. Must match the engine byte for byte."""
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _expected_signature(timestamp: str, nonce: str, body: dict[str, Any]) -> str:
    secret = settings.AI_ENGINE_SHARED_SECRET.encode("utf-8")
    message = b".".join([timestamp.encode(), nonce.encode(), canonical_payload(body)])
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_signature(request, body: dict[str, Any]) -> None:
    """Authenticate an inbound callback. Raises on any failure.

    Checks, in order: presence, clock skew, nonce reuse, then the signature
    itself. Cheap rejections come first so a flood of junk cannot force
    expensive HMAC computation.
    """
    timestamp = request.headers.get("X-Ferasha-Timestamp", "")
    nonce = request.headers.get("X-Ferasha-Nonce", "")
    signature = request.headers.get("X-Ferasha-Signature", "")

    if not (timestamp and nonce and signature):
        raise AuthenticationFailed("Callback signature headers are missing.")

    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise AuthenticationFailed("Malformed callback timestamp.") from exc

    if abs(int(time.time()) - sent_at) > MAX_SKEW_SECONDS:
        raise AuthenticationFailed("Callback timestamp is outside the accepted window.")

    # Single-use nonce. cache.add is atomic, so two concurrent replays cannot
    # both win the race.
    cache_key = f"ferasha:callback-nonce:{nonce}"
    if not cache.add(cache_key, "1", timeout=NONCE_TTL_SECONDS):
        logger.warning("Replayed callback nonce rejected: %s", nonce)
        raise AuthenticationFailed("Callback nonce has already been used.")

    expected = _expected_signature(timestamp, nonce, body)
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid callback signature for payload keys %s", sorted(body))
        raise AuthenticationFailed("Invalid callback signature.")


def parse_body(request) -> dict[str, Any]:
    """Parse the raw body.

    The signature covers the exact bytes received, so the raw body is used
    rather than DRF's parsed representation - re-serialising could change key
    order or spacing and invalidate an honest signature.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError({"detail": "Callback body must be valid JSON."}) from exc
    if not isinstance(payload, dict):
        raise ValidationError({"detail": "Callback body must be a JSON object."})
    return payload
