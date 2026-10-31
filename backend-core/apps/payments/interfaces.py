from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict, Any
from decimal import Decimal

class PaymentStatus(TypedDict):
    payment_id: str
    status: str # 'PENDING' | 'SUCCESS' | 'FAILED'
    amount: Decimal
    currency: str
    provider_reference: str
    timestamp: str

class PaymentGateway(ABC):
    """
    Abstract Base Class for all Payment Providers.
    This interface ensures the core business logic is decoupled from
    specific vendor SDKs (e.g., Razorpay, Stripe).
    """

    @abstractmethod
    def create_order(self, amount: Decimal, currency: str, order_id: str, customer_details: dict) -> PaymentStatus:
        """
        Initiate a payment session with the provider.
        Returns a standardized PaymentStatus containing the provider's payment ID.
        """
        pass

    @abstractmethod
    def verify_webhook(self, payload: Any, signature: str) -> bool:
        """
        Verify the authenticity of a webhook notification from the provider.
        Must implement HMAC verification using the provider's secret.
        """
        pass

    @abstractmethod
    def refund_payment(self, payment_id: str, amount: Decimal) -> bool:
        """
        Issue a full or partial refund for a specific payment.
        """
        pass
