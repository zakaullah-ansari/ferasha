"""Collecting payment for a placed order.

Two signals can confirm a payment, and both are honoured because either may
arrive first or alone: the browser posts the signature Razorpay's widget gives
it, and Razorpay posts a webhook. ``confirm_capture`` is idempotent, so
whichever lands second is a no-op.
"""

from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus
from apps.orders.state_machine import transition_order

from .gateways import WebhookEvent, WebhookKind, get_gateway, to_minor_units
from .models import Payment, PaymentStatus, PaymentWebhookEvent

logger = logging.getLogger(__name__)


class PaymentError(ValueError):
    """A payment request the customer cannot proceed with; message is customer-safe."""


@transaction.atomic
def initiate(order: Order) -> Payment:
    """Raise (or reuse) the provider order the customer will pay against."""
    # Lock the order so a double-click cannot raise two provider orders.
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != OrderStatus.PLACED:
        raise PaymentError("This order is not awaiting payment.")

    open_payment = (
        Payment.objects.filter(order=order, amount=order.grand_total)
        .exclude(status=PaymentStatus.CAPTURED)
        .first()
    )
    if open_payment is not None:
        return open_payment

    gateway = get_gateway()
    provider_order = gateway.create_order(
        amount=order.grand_total, currency=order.currency, receipt=order.order_number
    )
    if provider_order.amount_minor != to_minor_units(order.grand_total):
        # Never collect against an amount we did not ask for.
        raise PaymentError("The payment provider returned an unexpected amount.")
    return Payment.objects.create(
        order=order,
        provider=gateway.name,
        provider_order_id=provider_order.provider_order_id,
        amount=order.grand_total,
        currency=order.currency,
    )


@transaction.atomic
def confirm_capture(
    *,
    provider_order_id: str,
    provider_payment_id: str,
    amount_minor: int | None = None,
    source: str,
) -> Payment | None:
    """Mark a payment captured and move its order to PAYMENT_CONFIRMED.

    Returns ``None`` when ``provider_order_id`` is not one of ours.
    """
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(provider_order_id=provider_order_id)
        .first()
    )
    if payment is None:
        return None
    if payment.status == PaymentStatus.CAPTURED:
        return payment

    if amount_minor is not None and amount_minor != to_minor_units(payment.amount):
        logger.critical(
            "Payment %s captured %s minor units, expected %s. Order %s NOT confirmed.",
            provider_order_id, amount_minor, to_minor_units(payment.amount),
            payment.order.order_number,
        )
        raise PaymentError("Captured amount does not match the order.")

    payment.status = PaymentStatus.CAPTURED
    payment.provider_payment_id = provider_payment_id
    payment.captured_at = timezone.now()
    payment.failure_reason = ""
    payment.save(
        update_fields=[
            "status", "provider_payment_id", "captured_at", "failure_reason", "updated_at",
        ]
    )

    order = payment.order
    if order.status == OrderStatus.PLACED:
        transition_order(
            order,
            OrderStatus.PAYMENT_CONFIRMED,
            reason=f"Payment captured ({source})",
            metadata={"provider": payment.provider, "payment_id": provider_payment_id},
        )
    else:
        # e.g. the customer paid after an operator cancelled. Money is held
        # against an order that will not ship: a human must refund it.
        logger.error(
            "Payment %s captured for order %s in status %r; manual refund review needed.",
            provider_payment_id, order.order_number, order.status,
        )
    return payment


@transaction.atomic
def record_failure(*, provider_order_id: str, reason: str) -> None:
    Payment.objects.filter(provider_order_id=provider_order_id).exclude(
        status=PaymentStatus.CAPTURED
    ).update(status=PaymentStatus.FAILED, failure_reason=reason[:300], updated_at=timezone.now())


@transaction.atomic
def handle_webhook(event: WebhookEvent, *, provider: str, payload: dict) -> bool:
    """Apply a verified webhook once. Returns False for a redelivery."""
    try:
        # Savepoint scoped to the ledger insert alone, so only a duplicate
        # event id reads as "already applied" - never some other constraint.
        with transaction.atomic():
            PaymentWebhookEvent.objects.create(
                provider=provider,
                event_id=event.event_id,
                event_type=event.event_type,
                payload=payload,
            )
    except IntegrityError:
        return False

    if event.kind is WebhookKind.CAPTURED:
        try:
            payment = confirm_capture(
                provider_order_id=event.provider_order_id,
                provider_payment_id=event.provider_payment_id,
                amount_minor=event.amount_minor,
                source="webhook",
            )
        except PaymentError:
            # Already logged as critical. Keep the ledger row: redelivering
            # the same mismatched capture cannot make it right.
            return True
        if payment is None:
            logger.warning(
                "Webhook %s for unknown provider order %s",
                event.event_id, event.provider_order_id,
            )
    elif event.kind is WebhookKind.FAILED:
        record_failure(provider_order_id=event.provider_order_id, reason=event.failure_reason)
    return True
