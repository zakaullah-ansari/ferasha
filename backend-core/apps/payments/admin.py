"""Payments admin: ledgers, view only. Money moves through Razorpay, not here."""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.decorators import display

from apps.common.admin import ReadOnlyAdmin

from .models import Payment, PaymentStatus, PaymentWebhookEvent


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ("provider_order_id", "order", "amount", "status_badge", "captured_at", "created_at")
    list_filter = ("status", "provider", "created_at")
    search_fields = ("provider_order_id", "provider_payment_id", "order__order_number")
    list_select_related = ("order",)

    @display(
        description=_("Status"),
        ordering="status",
        label={
            PaymentStatus.CREATED.label: "info",
            PaymentStatus.CAPTURED.label: "success",
            PaymentStatus.FAILED.label: "danger",
        },
    )
    def status_badge(self, obj: Payment) -> str:
        return obj.get_status_display()


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "event_id", "provider", "received_at")
    list_filter = ("provider", "event_type")
    search_fields = ("event_id",)
