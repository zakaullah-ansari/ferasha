"""Liveness and readiness probes for the backend-core service."""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """GET /api/v1/health/ - liveness. Cheap, no dependency checks."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Liveness probe",
        description="Returns 200 as long as the process is serving requests.",
        responses={
            200: inline_serializer(
                name="HealthResponse",
                fields={
                    "status": serializers.CharField(),
                    "service": serializers.CharField(),
                },
            )
        },
        examples=[OpenApiExample("Alive", value={"status": "ok", "service": "backend-core"})],
        tags=["ops"],
    )
    def get(self, request):
        return Response({"status": "ok", "service": "backend-core"}, status=status.HTTP_200_OK)


class ReadinessView(APIView):
    """GET /api/v1/ready/ - readiness. Verifies Postgres and Redis."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Readiness probe",
        description=(
            "Verifies the database and cache are reachable. Returns 503 when any "
            "dependency is unavailable so the orchestrator withdraws the pod from "
            "the load balancer."
        ),
        responses={
            200: inline_serializer(
                name="ReadinessResponse",
                fields={
                    "status": serializers.CharField(),
                    "checks": serializers.DictField(child=serializers.CharField()),
                },
            ),
            503: OpenApiResponse(description="One or more dependencies are unavailable."),
        },
        tags=["ops"],
    )
    def get(self, request):
        checks: dict[str, str] = {}
        healthy = True

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except OperationalError as exc:
            logger.error("Readiness: database unavailable: %s", exc)
            checks["database"] = "unavailable"
            healthy = False

        try:
            cache.set("__readiness__", "1", timeout=5)
            checks["cache"] = "ok" if cache.get("__readiness__") == "1" else "degraded"
            healthy = healthy and checks["cache"] == "ok"
        except Exception as exc:
            logger.error("Readiness: cache unavailable: %s", exc)
            checks["cache"] = "unavailable"
            healthy = False

        return Response(
            {"status": "ready" if healthy else "not_ready", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
