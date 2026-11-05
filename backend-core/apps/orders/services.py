"""Order housekeeping that runs on a schedule rather than on a request."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Order, OrderStatus
from .state_machine import IllegalTransition, transition_order

logger = logging.getLogger(__name__)


def expire_unpaid_orders() -> list[str]:
    """Cancel orders left unpaid past UNPAID_ORDER_TTL_MINUTES; returns their numbers.

    Placing an order reserved its stock, and cancelling releases it (the state
    machine does both), so an abandoned checkout cannot keep a real piece
    showing as sold out. Each order is moved under its own row lock: one paid
    a moment ago, or already cancelled by someone else, is skipped rather than
    cancelled twice. A payment that lands after this (a slow gateway) is
    caught by payments.confirm_capture and flagged for a manual refund.
    """
    minutes = settings.UNPAID_ORDER_TTL_MINUTES
    cutoff = timezone.now() - timedelta(minutes=minutes)
    expired: list[str] = []
    for order in Order.objects.filter(status=OrderStatus.PLACED, placed_at__lt=cutoff).order_by("placed_at"):
        try:
            transition_order(
                order,
                OrderStatus.CANCELLED,
                reason=f"Automatically cancelled: not paid within {minutes} minutes. Stock released.",
            )
        except IllegalTransition:
            continue  # moved on since the query ran; the lock saw the newer state
        expired.append(order.order_number)
    if expired:
        logger.info("Cancelled %d unpaid order(s): %s", len(expired), ", ".join(expired))
    return expired
