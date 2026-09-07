"""HTTP surface for the GST engine."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import (
    GST_REGIMES,
    INDIAN_STATE_GST_CODES,
    VALUE_SLABBED_HSN,
    resolve_regime,
)
from .serializers import TaxQuoteRequestSerializer


class TaxQuoteView(APIView):
    """POST /api/v1/tax/quote/

    Stateless GST quotation. Open to anonymous callers so the storefront can
    show landed cost before sign-in; throttled by the global anon bucket.
    Quotes are advisory - the authoritative breakdown is snapshotted onto the
    order at checkout and never recomputed afterwards.
    """

    permission_classes = (AllowAny,)
    serializer_class = TaxQuoteRequestSerializer

    @extend_schema(
        summary="Quote GST for a basket",
        description=(
            "Stateless GST quotation for a prospective basket. Advisory only - the "
            "authoritative breakdown is snapshotted onto the order at checkout and "
            "is never recomputed afterwards."
        ),
        request=TaxQuoteRequestSerializer,
        responses={
            200: OpenApiResponse(description="Per-line and aggregate CGST/SGST/IGST breakdown."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["tax"],
    )
    def post(self, request):
        serializer = TaxQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.quote(), status=status.HTTP_200_OK)


class TaxRateReferenceView(APIView):
    """GET /api/v1/tax/reference/ - the rate card the engine applies."""

    permission_classes = (AllowAny,)
    serializer_class = None

    @extend_schema(
        summary="Applicable GST rate card",
        description=(
            "The rate card the engine currently applies, including the apparel "
            "value slab, flat-rated HSN codes and the regime history. Exposed so "
            "the storefront and finance tooling cannot drift from the engine."
        ),
        responses={
            200: inline_serializer(
                name="TaxRateReference",
                fields={
                    "home_state_code": drf_serializers.CharField(),
                    "home_country": drf_serializers.CharField(),
                    "regime": drf_serializers.CharField(),
                    "effective_from": drf_serializers.DateField(),
                    "apparel_slab": drf_serializers.DictField(),
                    "tailoring_service_rate": drf_serializers.CharField(),
                    "courier_service_rate": drf_serializers.CharField(),
                    "flat_rated_codes": drf_serializers.DictField(
                        child=drf_serializers.CharField()
                    ),
                    "permitted_rates": drf_serializers.ListField(
                        child=drf_serializers.CharField()
                    ),
                    "supported_states": drf_serializers.ListField(
                        child=drf_serializers.CharField()
                    ),
                    "regime_history": drf_serializers.ListField(child=drf_serializers.DictField()),
                },
            )
        },
        tags=["tax"],
    )
    def get(self, request):
        regime = resolve_regime()
        return Response(
            {
                "home_state_code": "MH",
                "home_country": "IN",
                "regime": regime.name,
                "effective_from": regime.effective_from.isoformat(),
                "apparel_slab": {
                    "threshold_per_piece": str(regime.apparel_threshold),
                    "rate_at_or_below": str(regime.apparel_rate_at_or_below),
                    "rate_above": str(regime.apparel_rate_above),
                    "applies_to_hsn": sorted(VALUE_SLABBED_HSN),
                },
                "tailoring_service_rate": str(regime.tailoring_service_rate),
                "courier_service_rate": str(regime.courier_service_rate),
                "flat_rated_codes": {k: str(v) for k, v in regime.flat_rate_codes().items()},
                "permitted_rates": sorted(str(r) for r in regime.permitted_rates),
                "supported_states": sorted(INDIAN_STATE_GST_CODES),
                "regime_history": [
                    {"name": r.name, "effective_from": r.effective_from.isoformat()}
                    for r in GST_REGIMES
                ],
            },
            status=status.HTTP_200_OK,
        )
