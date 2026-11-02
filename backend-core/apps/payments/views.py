"""Payment endpoints.

* ``POST /payments/orders/<order_number>/initiate/`` - provider order for the widget.
* ``POST /payments/orders/<order_number>/verify/``   - browser-side confirmation.
* ``POST /payments/webhooks/razorpay/``              - provider-side confirmation.
"""

from __future__ import annotations

import json
import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from . import services
from .gateways import (
    PaymentConfigurationError,
    PaymentGatewayError,
    RazorpayGateway,
    get_gateway,
)

logger = logging.getLogger(__name__)


def _customer_order(request, order_number: str) -> Order:
    # Another customer's order number 404s exactly like a missing one.
    return get_object_or_404(Order, order_number=order_number, customer=request.user)


class InitiatePaymentView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Open a payment for a placed order", request=None, tags=["payments"])
    def post(self, request, order_number: str):
        order = _customer_order(request, order_number)
        try:
            payment = services.initiate(order)
            client = get_gateway().client_config()
        except services.PaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except PaymentConfigurationError:
            logger.error("Payment initiation attempted with no gateway credentials.")
            return Response(
                {"detail": "Payments are temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PaymentGatewayError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(
            {
                **client,
                "provider_order_id": payment.provider_order_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "order_number": order.order_number,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentSerializer(serializers.Serializer):
    provider_order_id = serializers.CharField(max_length=64)
    provider_payment_id = serializers.CharField(max_length=64)
    signature = serializers.CharField(max_length=128)


class VerifyPaymentView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Confirm a payment from the checkout widget",
        request=VerifyPaymentSerializer,
        tags=["payments"],
    )
    def post(self, request, order_number: str):
        order = _customer_order(request, order_number)
        payload = VerifyPaymentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        # The provider order must belong to *this* order, or a valid signature
        # from a cheap order could confirm an expensive one.
        if not order.payments.filter(provider_order_id=data["provider_order_id"]).exists():
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if not get_gateway().verify_payment_signature(**data):
            logger.warning("Bad payment signature for order %s", order.order_number)
            return Response(
                {"detail": "Payment could not be verified."}, status=status.HTTP_400_BAD_REQUEST
            )

        services.confirm_capture(
            provider_order_id=data["provider_order_id"],
            provider_payment_id=data["provider_payment_id"],
            source="checkout",
        )
        order.refresh_from_db(fields=["status"])
        return Response({"order_number": order.order_number, "status": order.status})


class RazorpayWebhookView(APIView):
    """Signed by HMAC-SHA256 of the raw body; no user authentication applies."""

    permission_classes = (AllowAny,)
    # No authenticators: a stray Authorization header must not turn a valid
    # webhook into a 401. No throttle: the signature is the gate.
    authentication_classes = ()
    throttle_classes = ()

    @extend_schema(exclude=True)
    def post(self, request):
        gateway = RazorpayGateway()
        body = request.body  # raw bytes; must be read before request.data
        signature = request.headers.get("X-Razorpay-Signature", "")
        try:
            verified = gateway.verify_webhook_signature(body, signature)
        except PaymentConfigurationError:
            logger.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is unset.")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if not verified:
            logger.warning("Rejected Razorpay webhook with an invalid signature.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(body)
            event = gateway.parse_webhook(body, request.headers)
        except (ValueError, AttributeError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        applied = services.handle_webhook(event, provider=gateway.name, payload=payload)
        return Response({"applied": applied})
