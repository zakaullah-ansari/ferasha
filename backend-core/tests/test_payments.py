"""Payments: Razorpay adapter, browser confirmation, webhooks.

The real adapter runs - including its HMAC signature maths - with only the
outbound HTTP call stubbed, so these tests fail if the signature scheme drifts
from Razorpay's documented one.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from django.urls import reverse

from apps.orders.models import OrderEvent, OrderStatus
from apps.payments.gateways import RazorpayGateway
from apps.payments.models import Payment, PaymentStatus, PaymentWebhookEvent

KEY_ID = "rzp_test_key"
KEY_SECRET = "test-key-secret"
WEBHOOK_SECRET = "test-webhook-secret"
WEBHOOK = reverse("payments:razorpay-webhook")


def sign(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def razorpay_credentials(settings):
    settings.RAZORPAY_KEY_ID = KEY_ID
    settings.RAZORPAY_KEY_SECRET = KEY_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET


@pytest.fixture
def razorpay_api(monkeypatch):
    """Stub the HTTP call; record what would have been sent."""
    calls = []

    def fake_post(self, path, payload):
        calls.append((path, payload))
        return {"id": f"order_test{len(calls)}", "amount": payload["amount"], "currency": "INR"}

    monkeypatch.setattr(RazorpayGateway, "_post", fake_post)
    return calls


@pytest.fixture
def payment(placed_order, razorpay_api, auth_client):
    response = auth_client.post(
        reverse("payments:initiate", args=[placed_order.order_number])
    )
    assert response.status_code == 201, response.data
    return Payment.objects.get(provider_order_id=response.data["provider_order_id"])


def deliver(client, event: str, entity: dict, *, event_id: str, secret: str = WEBHOOK_SECRET):
    body = json.dumps({"event": event, "payload": {"payment": {"entity": entity}}}).encode()
    return client.post(
        WEBHOOK,
        data=body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=sign(secret, body),
        HTTP_X_RAZORPAY_EVENT_ID=event_id,
    )


def captured(payment, **overrides):
    return {
        "id": "pay_test1",
        "order_id": payment.provider_order_id,
        "amount": 1416000,
        "currency": "INR",
        "status": "captured",
        **overrides,
    }


@pytest.mark.django_db
class TestInitiate:
    def test_raises_a_provider_order_for_the_grand_total_in_paise(
        self, placed_order, razorpay_api, auth_client
    ):
        response = auth_client.post(
            reverse("payments:initiate", args=[placed_order.order_number])
        )

        assert response.status_code == 201
        assert response.data["key_id"] == KEY_ID
        assert response.data["amount"] == "14160.00"
        [(path, sent)] = razorpay_api
        assert path == "/orders"
        assert sent["amount"] == 1416000
        assert sent["receipt"] == placed_order.order_number

    def test_repeat_initiation_reuses_the_open_payment(self, payment, razorpay_api, auth_client):
        response = auth_client.post(
            reverse("payments:initiate", args=[payment.order.order_number])
        )

        assert response.data["provider_order_id"] == payment.provider_order_id
        assert len(razorpay_api) == 1

    def test_another_customers_order_is_not_found(self, placed_order, other_client):
        response = other_client.post(
            reverse("payments:initiate", args=[placed_order.order_number])
        )

        assert response.status_code == 404

    def test_missing_credentials_is_503_not_500(self, placed_order, auth_client, settings):
        settings.RAZORPAY_KEY_SECRET = ""

        response = auth_client.post(
            reverse("payments:initiate", args=[placed_order.order_number])
        )

        assert response.status_code == 503
        assert not Payment.objects.exists()


@pytest.mark.django_db
class TestBrowserConfirmation:
    def verify(self, client, payment, signature):
        return client.post(
            reverse("payments:verify", args=[payment.order.order_number]),
            {
                "provider_order_id": payment.provider_order_id,
                "provider_payment_id": "pay_test1",
                "signature": signature,
            },
            format="json",
        )

    def test_valid_signature_confirms_the_order(self, payment, auth_client):
        signature = sign(KEY_SECRET, f"{payment.provider_order_id}|pay_test1".encode())

        response = self.verify(auth_client, payment, signature)

        assert response.status_code == 200
        assert response.data["status"] == OrderStatus.PAYMENT_CONFIRMED
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CAPTURED
        assert OrderEvent.objects.filter(
            order=payment.order, to_status=OrderStatus.PAYMENT_CONFIRMED
        ).exists()

    def test_forged_signature_changes_nothing(self, payment, auth_client):
        response = self.verify(auth_client, payment, "0" * 64)

        assert response.status_code == 400
        payment.order.refresh_from_db()
        assert payment.order.status == OrderStatus.PLACED

    def test_a_payment_from_another_order_cannot_confirm_this_one(
        self, payment, auth_client, customer
    ):
        """A genuine signature for a cheap order must not confirm an expensive one."""
        from apps.cart import services as cart_services
        from apps.checkout import services as checkout_services
        from tests.conftest import MUMBAI
        from tests.factories import make_variant

        cart = cart_services.get_active_cart(customer)
        cart_services.add_item(cart, make_variant().pk)
        other_order = checkout_services.place_order(customer, dict(MUMBAI))

        response = auth_client.post(
            reverse("payments:verify", args=[other_order.order_number]),
            {
                "provider_order_id": payment.provider_order_id,
                "provider_payment_id": "pay_test1",
                "signature": sign(KEY_SECRET, f"{payment.provider_order_id}|pay_test1".encode()),
            },
            format="json",
        )

        assert response.status_code == 404
        other_order.refresh_from_db()
        assert other_order.status == OrderStatus.PLACED


@pytest.mark.django_db
class TestWebhook:
    def test_capture_confirms_the_order(self, payment, api_client):
        response = deliver(api_client, "payment.captured", captured(payment), event_id="evt_1")

        assert response.status_code == 200
        assert response.data["applied"] is True
        payment.order.refresh_from_db()
        assert payment.order.status == OrderStatus.PAYMENT_CONFIRMED

    def test_redelivery_is_a_no_op(self, payment, api_client):
        deliver(api_client, "payment.captured", captured(payment), event_id="evt_1")
        again = deliver(api_client, "payment.captured", captured(payment), event_id="evt_1")

        assert again.data["applied"] is False
        assert PaymentWebhookEvent.objects.count() == 1
        assert (
            OrderEvent.objects.filter(to_status=OrderStatus.PAYMENT_CONFIRMED).count() == 1
        )

    def test_browser_then_webhook_confirms_once(self, payment, auth_client, api_client):
        auth_client.post(
            reverse("payments:verify", args=[payment.order.order_number]),
            {
                "provider_order_id": payment.provider_order_id,
                "provider_payment_id": "pay_test1",
                "signature": sign(KEY_SECRET, f"{payment.provider_order_id}|pay_test1".encode()),
            },
            format="json",
        )
        deliver(api_client, "payment.captured", captured(payment), event_id="evt_2")

        assert (
            OrderEvent.objects.filter(to_status=OrderStatus.PAYMENT_CONFIRMED).count() == 1
        )

    def test_forged_webhook_is_rejected(self, payment, api_client):
        response = deliver(
            api_client, "payment.captured", captured(payment), event_id="evt_1", secret="wrong"
        )

        assert response.status_code == 400
        assert not PaymentWebhookEvent.objects.exists()
        payment.order.refresh_from_db()
        assert payment.order.status == OrderStatus.PLACED

    def test_short_capture_does_not_confirm(self, payment, api_client):
        deliver(api_client, "payment.captured", captured(payment, amount=100), event_id="evt_1")

        payment.order.refresh_from_db()
        assert payment.order.status == OrderStatus.PLACED
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CREATED

    def test_failure_is_recorded_and_a_later_retry_can_still_succeed(self, payment, api_client):
        failed = captured(payment, status="failed", error_description="Card declined")
        deliver(api_client, "payment.failed", failed, event_id="evt_1")

        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FAILED
        assert payment.failure_reason == "Card declined"

        deliver(api_client, "payment.captured", captured(payment, id="pay_2"), event_id="evt_2")

        payment.order.refresh_from_db()
        assert payment.order.status == OrderStatus.PAYMENT_CONFIRMED

    def test_unknown_provider_order_is_acknowledged(self, api_client):
        """A 2xx stops Razorpay retrying an event that is not ours forever."""
        entity = {"id": "pay_x", "order_id": "order_not_ours", "amount": 100}

        response = deliver(api_client, "payment.captured", entity, event_id="evt_1")

        assert response.status_code == 200

    def test_a_stray_authorization_header_does_not_block_delivery(self, payment, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-jwt")

        response = deliver(api_client, "payment.captured", captured(payment), event_id="evt_1")

        assert response.status_code == 200
