from __future__ import annotations

import logging
import hmac
import hashlib
from decimal import Decimal
from typing import Any
from .interfaces import PaymentGateway, PaymentStatus

logger = logging.getLogger(__name__)

class RazorpayAdapter(PaymentGateway):
    """
    Concrete implementation of PaymentGateway for Razorpay.
    Handles the specific API calls and signature verification for Razorpay.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def create_order(self, amount: Decimal, currency: str, order_id: str, customer_details: dict) -> PaymentStatus:
        """
        Creates a Razorpay order.
        Note: Razorpay expects amount in the smallest currency unit (e.g., Paise for INR).
        """
        # In a real implementation, this would use `import razorpay`
        # client = razorpay.Client(auth=(self.api_key, self.api_secret))
        # order = client.order.create({"amount": int(amount * 100), "currency": currency, "receipt": order_id})

        logger.info("Razorpay: Creating order for amount %s", amount)

        # Mocking the provider response for now
        return {
            "payment_id": f"pay_razor_{order_id}",
            "status": "PENDING",
            "amount": amount,
            "currency": currency,
            "provider_reference": f"rzp_order_{order_id}",
            "timestamp": "2026-10-31T10:00:00Z"
        }

    def verify_webhook(self, payload: Any, signature: str) -> bool:
        """
        Verify Razorpay webhook signature using HMAC-SHA256.
        """
        # payload is the raw request body as bytes
        # signature is the X-Razorpay-Signature header

        expected_signature = hmac.new(
            self.api_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        """
        Issue a refund via Razorpay API.
        """
        logger.info("Razorpay: Issuing refund for %s of amount %s", payment_id, amount)
        # Implementation would call client.payment.refund(...)
        return True
