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

from django.conf import settings

from apps.common.mail import first_name, frontend_url, send, wrap

from .tokens import make_email_verification_token, make_password_reset_token


def send_email_verification(user) -> None:
    """Email a single-use verification link. Safe to call repeatedly."""
    token = make_email_verification_token(user)
    url = frontend_url(settings.EMAIL_VERIFICATION_PATH, token=token)
    name = first_name(user.full_name)

    text = (
        f"Hello {name},\n\n"
        "Welcome to Ferasha. Please confirm your email address by opening the "
        f"link below.\n\n{url}\n\n"
        "This link is valid for 48 hours and can be used once.\n\n"
        "If you did not create a Ferasha account, you can ignore this message.\n"
    )
    html = wrap(
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
    send("Confirm your Ferasha email address", user.email, text, html)


def send_password_reset(user) -> None:
    """Email a single-use password reset link."""
    token = make_password_reset_token(user)
    url = frontend_url(settings.PASSWORD_RESET_PATH, token=token)
    name = first_name(user.full_name)

    text = (
        f"Hello {name},\n\n"
        "We received a request to reset the password on your Ferasha account. "
        f"Open the link below to choose a new one.\n\n{url}\n\n"
        "This link is valid for 1 hour and can be used once.\n\n"
        "If you did not request this, no action is needed - your password has "
        "not been changed.\n"
    )
    html = wrap(
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
    send("Reset your Ferasha password", user.email, text, html)


def send_password_changed_notice(user) -> None:
    """Out-of-band confirmation that a password changed.

    This is the tripwire that lets a user notice an account takeover, so it is
    sent on both self-service change and reset completion.
    """
    name = first_name(user.full_name)
    url = frontend_url(settings.PASSWORD_RESET_PATH)
    text = (
        f"Hello {name},\n\n"
        "The password on your Ferasha account was just changed, and all other "
        "sessions were signed out.\n\n"
        "If this was not you, reset your password immediately:\n"
        f"{url}\n"
    )
    html = wrap(
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
    send("Your Ferasha password was changed", user.email, text, html)
