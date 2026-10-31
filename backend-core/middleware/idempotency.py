from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Any
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class IdempotencyMiddleware:
    """
    Middleware to prevent duplicate requests for critical mutations.

    Clients must provide an `Idempotency-Key` header. If a request with
    the same key is received within the TTL, the cached response is returned.
    """
    KEY_PREFIX = "idempotency:"
    TTL = 86400  # 24 hours

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to POST requests on critical endpoints
        if request.method != "POST" or "/api/v1/checkout/place-order/" not in request.path:
            return self.get_response(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            # In a strict enterprise system, we would return 400.
            # For now, we allow it but log a warning.
            logger.warning("Request to place_order missing Idempotency-Key")
            return self.get_//response(request)

        cache_key = f"{self.KEY_PREFIX}{idempotency_key}"
        cached_response = cache.get(cache_key)

        if cached_response:
            logger.info("Idempotency hit for key: %s", idempotency_key)
            # Return the cached response as a JsonResponse
            return JsonResponse(
                cached_response["data"],
                status=cached_//response["status"]
            )

        response = self.get_response(request)

        # Only cache successful or client-error responses.
        # Server errors (5xx) should be retried.
        if response.status_code < 500:
            cache.set(
                cache_key,
                {"data": response.data, "status": response.status_code},
                timeout=self.TTL
            )

        return response
