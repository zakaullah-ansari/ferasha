"""Transactional email for the identity app.

Delivery is intentionally thin here. Phase 6 introduces the notification
service (email + WhatsApp fan-out with retry and delivery receipts); until
then these helpers post directly through Django's mail backend, which is
configured to console in development and SMTP in production.

Two rules are load-bearing and must survive the Phase 6 refactor:

* Sending must never raise into the request path. A mail outage must not turn
  a successful registration into a 500.
* The caller must not learn whether an address exists. These functions return
  ``None`` regardless of outcome.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .tokens import make_email_verification_token, make_password_reset_token

logger = logging.getLogger(__name__)


def _build_url(path: str, **params: str) -> str:
    base = settings.FRONTEND_BASE_URL
    if not base.endswith("/"):
        base += "/"
    url = urljoin(base, path.lstrip("/"))
    return f"{url}?{urlencode(params)}" if params else url


def _send(subject: str, to: str, text_body: str, html_body: str) -> None:
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


def _wrap(heading: str, body_html: str, cta_label: str, cta_url: str) -> str:
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


def send_email_verification(user) -> None:
    """Email a single-use verification link. Safe to call repeatedly."""
    token = make_email_verification_token(user)
    url = _build_url(settings.EMAIL_VERIFICATION_PATH, token=token)
    name = user.full_name.split()[0] if user.full_name else "there"

    text = (
        f"Hello {name},\n\n"
        "Welcome to Ferasha. Please confirm your email address by opening the "
        f"link below.\n\n{url}\n\n"
        "This link is valid for 48 hours and can be used once.\n\n"
        "If you did not create a Ferasha account, you can ignore this message.\n"
    )
    html = _wrap(
        heading=f"Welcome to Ferasha, {name}.",
        body_html=(
            "<p style='font-size:15px;line-height:1.7;margin:0 0 12px;'>Please confirm your "
            "email address so we can send you order confirmations, invoices and atelier "
            "updates.</p>"
            "<p style='font-size:13px;color:#6b5d4d;line-height:1.7;margin:0;'>This link is "
            "valid for 48 hours and can be used once. If you did not create a Ferasha "
            "account, you can safely ignore this message.</p>"
        ),
        cta_label="Confirm email",
        cta_url=url,
    )
    _send("Confirm your Ferasha email address", user.email, text, html)


def send_password_reset(user) -> None:
    """Email a single-use password reset link."""
    token = make_password_reset_token(user)
    url = _build_url(settings.PASSWORD_RESET_PATH, token=token)
    name = user.full_name.split()[0] if user.full_name else "there"

    text = (
        f"Hello {name},\n\n"
        "We received a request to reset the password on your Ferasha account. "
        f"Open the link below to choose a new one.\n\n{url}\n\n"
        "This link is valid for 1 hour and can be used once.\n\n"
        "If you did not request this, no action is needed - your password has "
        "not been changed.\n"
    )
    html = _wrap(
        heading="Reset your password",
        body_html=(
            "<p style='font-size:15px;line-height:1.7;margin:0 0 12px;'>We received a request "
            "to reset the password on your Ferasha account. Choose a new password using the "
            "button below.</p>"
            "<p style='font-size:13px;color:#6b5d4d;line-height:1.7;margin:0;'>This link is "
            "valid for one hour and can be used once. If you did not request it, no action is "
            "needed - your password has not been changed.</p>"
        ),
        cta_label="Choose a new password",
        cta_url=url,
    )
    _send("Reset your Ferasha password", user.email, text, html)


def send_password_changed_notice(user) -> None:
    """Out-of-band confirmation that a password changed.

    This is the tripwire that lets a user notice an account takeover, so it is
    sent on both self-service change and reset completion.
    """
    name = user.full_name.split()[0] if user.full_name else "there"
    url = _build_url(settings.PASSWORD_RESET_PATH)
    text = (
        f"Hello {name},\n\n"
        "The password on your Ferasha account was just changed, and all other "
        "sessions were signed out.\n\n"
        "If this was not you, reset your password immediately:\n"
        f"{url}\n"
    )
    html = _wrap(
        heading="Your password was changed",
        body_html=(
            "<p style='font-size:15px;line-height:1.7;margin:0 0 12px;'>The password on your "
            "Ferasha account was just changed, and every other signed-in session was ended.</p>"
            "<p style='font-size:13px;color:#6b5d4d;line-height:1.7;margin:0;'>If this was not "
            "you, reset your password immediately using the button below and contact us.</p>"
        ),
        cta_label="Reset password",
        cta_url=url,
    )
    _send("Your Ferasha password was changed", user.email, text, html)
