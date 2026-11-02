"""Checkout API: quote, then place.

* ``POST /checkout/quote/``       - price the bag for an address. No side effects.
* ``POST /checkout/place-order/`` - create the order. Requires Idempotency-Key.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.idempotency import HEADER, idempotent
from apps.orders.models import Order
from apps.orders.serializers import OrderDetailSerializer

from . import services
from .serializers import CheckoutRequestSerializer


class CheckoutViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def _validated(self, request) -> dict:
        payload = CheckoutRequestSerializer(data=request.data, context={"request": request})
        payload.is_valid(raise_exception=True)
        return payload.validated_data

    @extend_schema(summary="Price the bag for a delivery address", tags=["checkout"])
    @action(detail=False, methods=["post"])
    def quote(self, request):
        data = self._validated(request)
        try:
            priced = services.quote(request.user, data["address"])
        except services.CheckoutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(priced.as_dict())

    @extend_schema(
        summary="Place the order",
        tags=["checkout"],
        parameters=[OpenApiParameter(HEADER, location="header", required=True)],
    )
    @action(detail=False, methods=["post"], url_path="place-order")
    @idempotent("checkout.place-order")
    def place_order(self, request):
        data = self._validated(request)
        try:
            order = services.place_order(
                request.user,
                data["address"],
                expected_grand_total=data.get("expected_grand_total"),
                customer_notes=data["customer_notes"],
            )
        except services.PriceChanged as exc:
            return Response(
                {"detail": str(exc), "quote": exc.quote.as_dict()},
                status=status.HTTP_409_CONFLICT,
            )
        except services.CheckoutError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        order = (
            Order.objects.select_related("tax_snapshot", "customer")
            .prefetch_related("lines__tailoring_spec", "events")
            .get(pk=order.pk)
        )
        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
