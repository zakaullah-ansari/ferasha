"""Orders admin.

Orders are written by checkout and are contracts: money, lines and the tax
snapshot are read-only here. The only way to move an order is the "Change
status" action, which goes through `transition_order` - so illegal jumps are
refused, cancellations release stock, and every change lands in the audit trail
with the staff member's name.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from apps.common.admin import ReadOnlyStackedInline, ReadOnlyTabularInline
from apps.payments.models import Payment

from .models import Order, OrderEvent, OrderLine, OrderStatus, OrderTaxSnapshot
from .state_machine import IllegalTransition, available_transitions, transition_order

#: Badge colour per status in lists.
STATUS_COLOURS = {
    OrderStatus.DRAFT.label: "info",
    OrderStatus.PLACED.label: "warning",
    OrderStatus.PAYMENT_CONFIRMED.label: "primary",
    OrderStatus.IN_ATELIER.label: "primary",
    OrderStatus.MEASUREMENT_REVIEW.label: "warning",
    OrderStatus.STITCHING.label: "primary",
    OrderStatus.QUALITY_CHECK.label: "primary",
    OrderStatus.PACKED.label: "primary",
    OrderStatus.SHIPPED.label: "info",
    OrderStatus.DELIVERED.label: "success",
    OrderStatus.RETURN_REQUESTED.label: "warning",
    OrderStatus.RETURNED.label: "warning",
    OrderStatus.REFUNDED.label: "danger",
    OrderStatus.CANCELLED.label: "danger",
}


class ChangeStatusForm(BaseDialogForm):
    status = forms.ChoiceField(label=_("Move order to"), widget=UnfoldAdminSelectWidget)
    reason = forms.CharField(
        label=_("Note for the order history"),
        max_length=300,
        required=False,
        widget=UnfoldAdminTextInputWidget,
    )

    def __init__(self, request, object_id=None, *args, **kwargs):
        super().__init__(request, object_id, *args, **kwargs)
        order = get_object_or_404(Order, pk=object_id)
        # Only what the state machine allows from here; it re-checks anyway.
        self.fields["status"].choices = [
            (status, OrderStatus(status).label)
            for status in OrderStatus.values
            if status in available_transitions(order.status)
        ]


class OrderLineInline(ReadOnlyTabularInline):
    model = OrderLine
    fields = ("sku", "product_name", "variant_label", "quantity", "unit_price", "is_bespoke")
    readonly_fields = fields


class OrderTaxSnapshotInline(ReadOnlyStackedInline):
    model = OrderTaxSnapshot
    verbose_name_plural = _("Tax as invoiced")
    fields = (
        ("regime_name", "supply_type"),
        ("place_of_supply_state", "place_of_supply_country", "state_gst_code"),
        ("taxable_value", "tax_total", "grand_total"),
        ("cgst_total", "sgst_total", "igst_total"),
    )
    readonly_fields = (
        "regime_name", "supply_type", "place_of_supply_state", "place_of_supply_country",
        "state_gst_code", "taxable_value", "tax_total", "grand_total",
        "cgst_total", "sgst_total", "igst_total",
    )


class PaymentInline(ReadOnlyTabularInline):
    model = Payment
    fields = ("provider", "provider_order_id", "provider_payment_id", "amount", "status", "captured_at")
    readonly_fields = fields


class OrderEventInline(ReadOnlyTabularInline):
    model = OrderEvent
    verbose_name_plural = _("History")
    fields = ("created_at", "from_status", "to_status", "actor", "reason")
    readonly_fields = fields
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("order_number", "customer_display", "status_badge", "grand_total", "placed_at")
    list_filter = ("status", "supply_type", "placed_at")
    search_fields = ("order_number", "customer__email", "customer__full_name", "guest_email")
    list_select_related = ("customer",)
    date_hierarchy = "placed_at"
    inlines = (OrderLineInline, OrderTaxSnapshotInline, PaymentInline, OrderEventInline)
    actions_detail = ("change_status",)

    fieldsets = (
        (None, {"fields": ("order_number", "status", "customer", "guest_email", "guest_phone", "placed_at")}),
        (_("Money"), {
            "fields": (("subtotal", "discount_total"), ("shipping_charge", "tax_total"), "grand_total", "currency"),
        }),
        (_("Delivery"), {
            "fields": ("shipping_address", "billing_address", "customer_gstin",
                       ("place_of_supply_state", "place_of_supply_country", "supply_type", "supply_date")),
        }),
        (_("Notes"), {"fields": ("customer_notes", "internal_notes")}),
    )

    def get_readonly_fields(self, request, obj=None):
        # Everything but the internal note: the order is a contract.
        return [
            field.name for field in Order._meta.fields if field.name != "internal_notes"
        ]

    def has_add_permission(self, request) -> bool:
        return False  # orders come from checkout

    def has_delete_permission(self, request, obj=None) -> bool:
        return False  # cancel instead; the record is a tax document

    @display(description=_("Customer"), ordering="customer__email")
    def customer_display(self, obj: Order) -> str:
        return obj.customer.email if obj.customer_id else f"{obj.guest_email} (guest)"

    @display(description=_("Status"), ordering="status", label=STATUS_COLOURS)
    def status_badge(self, obj: Order) -> str:
        return obj.get_status_display()

    def has_change_status_permission(self, request, object_id=None) -> bool:
        if not request.user.has_perm("orders.change_order"):
            return False
        if object_id is None:
            return True
        order = Order.objects.filter(pk=object_id).only("status").first()
        return bool(order and available_transitions(order.status))

    @action(
        description=_("Change status"),
        url_path="change-status",
        permissions=["change_status"],
        variant=ActionVariant.PRIMARY,
        icon="swap_horiz",
        dialog={
            "title": _("Change order status"),
            "description": _(
                "Moves the order and records it in its history under your name. "
                "Cancelling returns its pieces to stock."
            ),
            "form_class": ChangeStatusForm,
            "form_submit_text": _("Change status"),
        },
    )
    def change_status(self, request, form, object_id):
        order = get_object_or_404(Order, pk=object_id)
        target = form.cleaned_data["status"]
        try:
            transition_order(
                order, target, actor=request.user, reason=form.cleaned_data["reason"]
            )
        except IllegalTransition as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request, _("Order %(number)s is now %(status)s.") % {
                    "number": order.order_number, "status": OrderStatus(target).label,
                }
            )
        return _navigate(request, reverse("admin:orders_order_change", args=[object_id]))


def _navigate(request, url: str) -> HttpResponse:
    """Reload the page after a dialog action.

    The dialog posts over htmx, which would follow a plain redirect in the
    background and swap the result into the dialog, leaving the page showing
    the old status. HX-Redirect makes htmx do a real navigation instead.
    """
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)
