from __future__ import annotations

import logging
from typing import Any
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .adapters.razorpay import RazorpayAdapter
from apps.orders.models import Order, OrderStatus
from apps.orders.state_machine import OrderStateMachine
from django.conf import settings

logger = logging.getLogger(__name__)

class PaymentWebhookView(APIView):
    """
    Endpoint for Payment Provider webhooks.
    Handles async notifications (e.g., payment.captured) to finalize orders.
    """
    permission_classes = [AllowAny] # Webhooks are called by external servers

    def post(self, request):
        # 1. Initialize the adapter based on current config
        # In a production system, this would be a factory: PaymentGatewayFactory.get_provider()
        adapter = RazorpayAdapter(
            api_key=settings.RAZORPAY_KEY,
            api_secret=settings.RAZORPAY_SECRET
        )

        # 2. Security: Verify the HMAC signature
        signature = request.headers.get("X-Razorpay-Signature")
        if not signature:
            logger.warning("Payment webhook received without signature header.")
            return Response({"detail": "Missing signature"}, status=status.HTTP_400_BAD_REQUEST)

        # We need the raw body for HMAC verification
        raw_payload = request.body
        if not adapter.verify_webhook(raw_payload, signature):
            logger.error("Invalid payment webhook signature detected!")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        # 3. Process the event
        data = request.data
        event = data.get("event")
        payload = data.get("payload", {}).get("payment", {})
        order_id = payload.get("order_id")

        if event == "payment.captured":
            return self._handle_payment_success(order_id)
        elif event == "payment.failed":
            return self._handle_payment_failure(order_id)

        return Response({"detail": "Event ignored"}, status=status.HTTP_200_OK)

    def _handle_payment_success(self, order_id: str):
        try:
            order = Order.objects.get(id=order_id)

            # Transition state: PLACED -> PAYMENT_CONFIRMED
            OrderStateMachine.transition(order, OrderStatus.PAYMENT_CONFIRMED)

            logger.info("Order %s successfully confirmed via webhook.", order_id)
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            logger.error("Webhook received for non-existent order: %s", order_id)
            return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    def _handle_payment_failure(self, order_id: str):
        try:
            order = Order.objects.get(id=order_id)

            # Transition state: PLACED -> PAYMENT_FAILED
            OrderStateMachine.transition(order, OrderStatus.PAYMENT_FAILED)

            logger.info("Order %s marked as failed via webhook.", order_id)
            return Response({"status": "failure_recorded"}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
