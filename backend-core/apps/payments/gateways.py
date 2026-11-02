"""Payment provider adapters.

Business logic in ``services`` talks to ``PaymentGateway`` only. Swapping or
adding a provider means a new subclass and a ``PAYMENT_GATEWAY`` setting, with
no change to checkout or order code.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class PaymentGatewayError(RuntimeError):
    """The provider could not be reached or refused the request."""


class PaymentConfigurationError(PaymentGatewayError):
    """Credentials for the configured provider are missing."""


def to_minor_units(amount: Decimal) -> int:
    """Rupees to paise. INR has two decimal places; amounts are already 2dp."""
    return int((amount * 100).to_integral_value())


@dataclass(frozen=True, slots=True)
class ProviderOrder:
    provider_order_id: str
    amount_minor: int
    currency: str


class WebhookKind(StrEnum):
    CAPTURED = "captured"
    FAILED = "failed"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    """A provider webhook, normalised to what our services act on."""

    event_id: str
    event_type: str
    kind: WebhookKind
    provider_order_id: str = ""
    provider_payment_id: str = ""
    amount_minor: int | None = None
    failure_reason: str = ""


class PaymentGateway(ABC):
    name: str

    @abstractmethod
    def create_order(self, *, amount: Decimal, currency: str, receipt: str) -> ProviderOrder:
        """Raise a provider-side order for ``amount`` and return its id."""

    @abstractmethod
    def verify_payment_signature(
        self, *, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        """Check the signature the provider's checkout widget hands the browser."""

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Check a webhook delivery against the raw request bytes."""

    @abstractmethod
    def parse_webhook(self, body: bytes, headers) -> WebhookEvent:
        """Normalise a verified webhook delivery."""

    @abstractmethod
    def client_config(self) -> dict[str, str]:
        """Public values the browser needs to open the provider's checkout."""


def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class RazorpayGateway(PaymentGateway):
    """Razorpay Orders API + Standard Checkout.

    https://razorpay.com/docs/api/orders/create/
    https://razorpay.com/docs/payments/server-integration/python/payment-gateway/build-integration/
    """

    name = "razorpay"
    API_BASE = "https://api.razorpay.com/v1"
    TIMEOUT_SECONDS = 10
    CAPTURE_EVENTS = frozenset({"payment.captured", "order.paid"})
    FAILURE_EVENTS = frozenset({"payment.failed"})

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self.key_id = key_id if key_id is not None else settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret if key_secret is not None else settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = (
            webhook_secret if webhook_secret is not None else settings.RAZORPAY_WEBHOOK_SECRET
        )

    def _require(self, *values: str) -> None:
        if not all(values):
            raise PaymentConfigurationError("Razorpay credentials are not configured.")

    def _post(self, path: str, payload: dict) -> dict:
        credentials = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode()
        request = urllib.request.Request(  # noqa: S310 - fixed https:// base URL
            f"{self.API_BASE}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:  # noqa: S310
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            logger.error("Razorpay %s refused (%s): %s", path, exc.code, detail)
            raise PaymentGatewayError("The payment provider refused the request.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.error("Razorpay %s unreachable: %s", path, exc)
            raise PaymentGatewayError("The payment provider is unreachable.") from exc

    def create_order(self, *, amount: Decimal, currency: str, receipt: str) -> ProviderOrder:
        self._require(self.key_id, self.key_secret)
        body = self._post(
            "/orders",
            {"amount": to_minor_units(amount), "currency": currency, "receipt": receipt[:40]},
        )
        return ProviderOrder(
            provider_order_id=body["id"], amount_minor=body["amount"], currency=body["currency"]
        )

    def verify_payment_signature(
        self, *, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        self._require(self.key_secret)
        message = f"{provider_order_id}|{provider_payment_id}".encode()
        return hmac.compare_digest(_hmac_hex(self.key_secret, message), signature or "")

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        # The webhook secret is set per webhook in the Razorpay dashboard and is
        # deliberately distinct from the API key secret.
        self._require(self.webhook_secret)
        return hmac.compare_digest(_hmac_hex(self.webhook_secret, body), signature or "")

    def parse_webhook(self, body: bytes, headers) -> WebhookEvent:
        data = json.loads(body)
        event_type = data.get("event", "")
        payment = (data.get("payload") or {}).get("payment", {}).get("entity") or {}
        # Razorpay sends a unique id per event in this header; redeliveries of
        # the same event repeat it.
        event_id = headers.get("X-Razorpay-Event-Id") or hashlib.sha256(body).hexdigest()

        if event_type in self.CAPTURE_EVENTS:
            kind = WebhookKind.CAPTURED
        elif event_type in self.FAILURE_EVENTS:
            kind = WebhookKind.FAILED
        else:
            kind = WebhookKind.IGNORED

        return WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            kind=kind,
            provider_order_id=payment.get("order_id") or "",
            provider_payment_id=payment.get("id") or "",
            amount_minor=payment.get("amount"),
            failure_reason=(payment.get("error_description") or "")[:300],
        )

    def client_config(self) -> dict[str, str]:
        self._require(self.key_id)
        return {"provider": self.name, "key_id": self.key_id}


@cache
def _gateway_class(path: str) -> type[PaymentGateway]:
    return import_string(path)


def get_gateway() -> PaymentGateway:
    return _gateway_class(settings.PAYMENT_GATEWAY)()
