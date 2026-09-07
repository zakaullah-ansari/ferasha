"""HTTP surface for the GST engine."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import (
    APPAREL_RATE_ABOVE_THRESHOLD,
    APPAREL_RATE_BELOW_THRESHOLD,
    APPAREL_SLAB_THRESHOLD,
    FLAT_RATE_HSN,
    INDIAN_STATE_GST_CODES,
    SERVICE_RATE_STANDARD,
    VALUE_SLABBED_HSN,
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

    def post(self, request):
        serializer = TaxQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.quote(), status=status.HTTP_200_OK)


class TaxRateReferenceView(APIView):
    """GET /api/v1/tax/reference/ - the rate card the engine applies."""

    permission_classes = (AllowAny,)

    def get(self, request):
        return Response(
            {
                "home_state_code": "MH",
                "home_country": "IN",
                "apparel_slab": {
                    "threshold_per_piece": str(APPAREL_SLAB_THRESHOLD),
                    "rate_at_or_below": str(APPAREL_RATE_BELOW_THRESHOLD),
                    "rate_above": str(APPAREL_RATE_ABOVE_THRESHOLD),
                    "applies_to_hsn": sorted(VALUE_SLABBED_HSN),
                },
                "service_rate": str(SERVICE_RATE_STANDARD),
                "flat_rated_codes": {k: str(v) for k, v in FLAT_RATE_HSN.items()},
                "supported_states": sorted(INDIAN_STATE_GST_CODES),
            },
            status=status.HTTP_200_OK,
        )
