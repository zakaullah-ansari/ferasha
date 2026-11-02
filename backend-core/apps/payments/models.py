"""Payment attempts and the webhook ledger."""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class PaymentStatus(models.TextChoices):
    CREATED = "created", _("Created")
    CAPTURED = "captured", _("Captured")
    FAILED = "failed", _("Failed")


class Payment(BaseModel):
    """One provider-side order raised to collect an order's grand total.

    A failed card attempt does not end the Payment: Razorpay lets the customer
    retry against the same provider order, so FAILED can still become CAPTURED.
    """

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="payments"
    )
    provider = models.CharField(max_length=32)
    provider_order_id = models.CharField(max_length=64, unique=True)
    provider_payment_id = models.CharField(max_length=64, blank=True, db_index=True)
    #: Amount requested from the provider, frozen when the Payment is raised.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.CREATED
    )
    failure_reason = models.CharField(max_length=300, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")), name="payment_amount_positive"
            ),
            # Money is collected once per order. A second capture is a refund
            # case for a human, not something to record silently.
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status="captured"),
                name="one_captured_payment_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_order_id} ({self.status})"


class PaymentWebhookEvent(models.Model):
    """Every webhook delivery we accepted, keyed by the provider's event id.

    Providers deliver at least once. The unique key makes a redelivery a no-op
    instead of a second state change.
    """

    id = models.BigAutoField(primary_key=True)
    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-received_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"], name="unique_webhook_event_per_provider"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id}"
