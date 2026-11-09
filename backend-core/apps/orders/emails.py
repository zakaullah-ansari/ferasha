"""What the customer is told when their order moves on.

Only the moments a customer would want to hear about. In the atelier, quality
check and packing are internal steps; "being stitched" is news only for a
bespoke piece. An unpaid order that lapses is not mentioned: no money moved,
and an email would only be noise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.utils.html import escape

from apps.common.mail import first_name, format_inr, frontend_url, send, wrap

from .models import Order, OrderStatus

logger = logging.getLogger(__name__)

S = OrderStatus

P = "font-size:15px;line-height:1.7;margin:0 0 12px;"
NOTE = "font-size:13px;color:#6b5d4d;line-height:1.7;margin:0 0 12px;"


@dataclass(frozen=True)
class Message:
    subject: str
    heading: str
    lead: str
    note: str = ""


def _message(order: Order, from_status: str, to_status: str) -> Message | None:
    number = order.order_number
    bespoke = any(line.is_bespoke for line in order.lines.all())
    if to_status == S.PAYMENT_CONFIRMED:
        return Message(
            f"Your Ferasha order {number} is confirmed",
            "Thank you, your order is confirmed",
            "We have your payment and your order is with the atelier. We will write again when it is on its way.",
            "Bespoke pieces are stitched to the measurements you confirmed; each product page gives its stitching time."
            if bespoke
            else "",
        )
    if to_status == S.STITCHING and bespoke:
        return Message(
            f"Your Ferasha order {number} is being stitched",
            "Your garment is being stitched",
            "Your measurements are confirmed and our tailors have started on your piece.",
        )
    if to_status == S.SHIPPED:
        return Message(
            f"Your Ferasha order {number} has shipped",
            "Your order is on its way",
            "Your order has left the atelier. The courier's tracking details follow separately.",
        )
    if to_status == S.DELIVERED:
        return Message(
            f"Your Ferasha order {number} has been delivered",
            "Your order has been delivered",
            "We hope you love it. If anything is not right, see our returns page or call the atelier.",
        )
    if to_status == S.CANCELLED and from_status != S.PLACED:
        return Message(
            f"Your Ferasha order {number} has been cancelled",
            "Your order has been cancelled",
            "Your order has been cancelled. Your payment will be refunded to the original payment method.",
            "If you did not ask for this, please call the atelier.",
        )
    if to_status == S.REFUNDED:
        return Message(
            f"Your Ferasha order {number} has been refunded",
            "Your refund has been issued",
            "We have refunded your payment to the original payment method. Banks usually take 5 to 7 working days to show it.",
        )
    return None


def _recipient(order: Order) -> tuple[str, str]:
    if order.customer_id:
        return order.customer.email, first_name(order.customer.full_name)
    recipient = (order.shipping_address or {}).get("recipient_name", "")
    return order.guest_email, first_name(recipient)


def send_status_email(order_id, from_status: str, to_status: str) -> None:
    """Email the customer about one status change, if it is one they would want to hear about.

    Runs after the change has committed; never raises into the caller.
    """
    try:
        order = Order.objects.select_related("customer").prefetch_related("lines").get(pk=order_id)
        message = _message(order, from_status, to_status)
        if message is None:
            return
        to, name = _recipient(order)
        if not to:
            return
        url = frontend_url(f"/orders/{order.order_number}")
        lines = list(order.lines.all())
        total = format_inr(order.grand_total)

        text = "\n".join(
            [
                f"Hello {name},",
                "",
                message.lead,
                *([message.note] if message.note else []),
                "",
                f"Order {order.order_number}",
                *(f"  {line.quantity} x {line.product_name} ({line.variant_label})" for line in lines),
                f"  Total: {total}",
                "",
                f"Follow your order: {url}",
            ]
        )
        rows = "".join(
            f"<tr><td style='padding:6px 0;font-size:14px;'>{escape(line.product_name)}"
            f"<br><span style='font-size:12px;color:#8a7c6c;'>{escape(line.variant_label)} · Qty {line.quantity}</span></td></tr>"
            for line in lines
        )
        html = wrap(
            heading=message.heading,
            body_html=(
                f"<p style='{P}'>Hello {escape(name)},</p>"
                f"<p style='{P}'>{escape(message.lead)}</p>"
                + (f"<p style='{NOTE}'>{escape(message.note)}</p>" if message.note else "")
                + f"<p style='{NOTE}'>Order {escape(order.order_number)}</p>"
                f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'>{rows}</table>"
                f"<p style='{P}margin-top:12px;'>Total: <strong>{escape(total)}</strong></p>"
            ),
            cta_label="Follow your order",
            cta_url=url,
        )
        send(message.subject, to, text, html)
    except Exception:
        logger.exception("Could not email order %s about %s -> %s", order_id, from_status, to_status)
