"""Idempotency-Key support for mutations that must happen exactly once.

Applied as a decorator on DRF views rather than as Django middleware: JWT
authentication runs inside DRF's dispatch, so a middleware sees every caller as
anonymous and cannot scope keys per customer. Unscoped keys would let one
customer replay another's response by guessing their key.

Contract (after the IETF httpapi Idempotency-Key draft):

* The client sends ``Idempotency-Key: <opaque, 8-255 chars>``.
* A repeat with the same key and same body returns the stored response, with
  ``Idempotent-Replayed: true``.
* The same key with a different body is a client bug: 422.
* A repeat while the first is still running: 409, the client retries later.
* Only 2xx responses are stored. A refused request changed nothing, so running
  it again is safe - and necessary: after a "prices changed" 409 the client
  re-quotes and retries, and must not be handed the stale refusal.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotent-Replayed"
RESULT_TTL = 24 * 60 * 60
#: Longer than any request should take; short enough that a crashed worker's
#: lock does not block the customer for long.
LOCK_TTL = 60


def _fingerprint(request) -> str:
    body = json.dumps(request.data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def idempotent(scope: str, *, required: bool = True) -> Callable:
    """Make a DRF view method idempotent per (scope, user, key)."""

    def decorator(view_method: Callable) -> Callable:
        @functools.wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            key = request.headers.get(HEADER, "").strip()
            if not key:
                if required:
                    return Response(
                        {"detail": f"An {HEADER} header is required for this request."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return view_method(self, request, *args, **kwargs)
            if not 8 <= len(key) <= 255:
                return Response(
                    {"detail": f"{HEADER} must be 8-255 characters."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            owner = request.user.pk if request.user.is_authenticated else "anon"
            # Hash the client-chosen key so it cannot inject into the cache key.
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            result_key = f"idem:{scope}:{owner}:{digest}"
            lock_key = f"{result_key}:lock"
            fingerprint = _fingerprint(request)

            stored = cache.get(result_key)
            if stored is not None:
                return _replay(stored, fingerprint)

            if not cache.add(lock_key, fingerprint, timeout=LOCK_TTL):
                # Lost the race to a concurrent twin. It may have finished
                # between our read and our add; prefer its answer if so.
                stored = cache.get(result_key)
                if stored is not None:
                    return _replay(stored, fingerprint)
                return Response(
                    {"detail": "An identical request is already in progress."},
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                response = view_method(self, request, *args, **kwargs)
                if 200 <= response.status_code < 300:
                    cache.set(
                        result_key,
                        {
                            "fingerprint": fingerprint,
                            "status": response.status_code,
                            "data": response.data,
                        },
                        timeout=RESULT_TTL,
                    )
                return response
            finally:
                cache.delete(lock_key)

        return wrapper

    return decorator


def _replay(stored: dict, fingerprint: str) -> Response:
    if stored["fingerprint"] != fingerprint:
        return Response(
            {"detail": f"This {HEADER} was already used with a different request body."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    response = Response(stored["data"], status=stored["status"])
    response[REPLAY_HEADER] = "true"
    return response
