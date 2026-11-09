"""Transactional email shared by every app.

Two rules are load-bearing and must survive the Phase 6 notification service:

* Sending never raises into the caller. A mail outage must not turn a
  registration or an order update into a 500.
* Everything a customer typed (a name, a product a vendor named) is escaped
  before it reaches HTML. `wrap` escapes what it inserts; callers building
  `body_html` escape their own values (django.utils.html.escape).
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger(__name__)


def frontend_url(path: str, **params: str) -> str:
    base = settings.FRONTEND_BASE_URL
    if not base.endswith("/"):
        base += "/"
    url = urljoin(base, path.lstrip("/"))
    return f"{url}?{urlencode(params)}" if params else url


def first_name(full_name: str) -> str:
    return full_name.split()[0] if full_name.strip() else "there"


def format_inr(amount: Decimal) -> str:
    """₹14,160 and ₹1,89,000: whole rupees, Indian digit grouping (as the storefront shows)."""
    rupees = int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    digits = str(abs(rupees))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    grouped = ",".join([*groups, tail]) if groups else tail
    return f"{'-' if rupees < 0 else ''}₹{grouped}"


def send(subject: str, to: str, text_body: str, html_body: str) -> None:
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    message.attach_alternative(html_body, "text/html")
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to deliver %r to %s", subject, to)


def wrap(heading: str, body_html: str, cta_label: str, cta_url: str) -> str:
    heading, cta_label, cta_url = escape(heading), escape(cta_label), escape(cta_url)
    return f"""\
<!doctype html>
<html lang="en">
  <body style="margin:0;padding:32px 0;background:#faf7f2;font-family:Georgia,'Times New Roman',serif;color:#2b2118;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border:1px solid #e8ded0;border-radius:4px;">
          <tr><td style="padding:32px 40px 8px;text-align:center;">
            <div style="font-size:22px;letter-spacing:0.28em;text-transform:uppercase;">Ferasha</div>
            <div style="font-size:10px;letter-spacing:0.16em;color:#9a8b76;text-transform:uppercase;">Modest luxury</div>
          </td></tr>
          <tr><td style="padding:8px 40px 0;">
            <h1 style="font-size:20px;font-weight:normal;margin:0 0 16px;">{heading}</h1>
            {body_html}
          </td></tr>
          <tr><td style="padding:24px 40px 40px;" align="center">
            <a href="{cta_url}"
               style="display:inline-block;padding:13px 30px;background:#2b2118;color:#ffffff;
                      text-decoration:none;font-size:12px;letter-spacing:0.18em;
                      text-transform:uppercase;">{cta_label}</a>
            <p style="font-size:11px;color:#8a7c6c;margin:20px 0 0;line-height:1.6;">
              If the button does not work, copy this link into your browser:<br>
              <span style="word-break:break-all;">{cta_url}</span>
            </p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""
