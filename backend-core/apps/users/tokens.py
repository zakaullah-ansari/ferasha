"""Signed, single-use, time-limited tokens for email verification and
password reset.

Built on Django's ``TimestampSigner`` rather than a bespoke scheme. Two
properties matter:

* **Single use.** The payload embeds a fingerprint derived from state that
  changes when the token is consumed (the password hash for a reset, the
  verification timestamp for an email). A replayed token therefore fails even
  before it expires.
* **No enumeration.** Issuing a token never reveals whether an account exists;
  the caller-facing views always return the same response.
"""

from __future__ import annotations

import hashlib

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

# These are signer salts (domain separation), not secrets. The signing key is
# SECRET_KEY. Distinct salts are what stop a verification token being replayed
# as a password-reset token.
EMAIL_VERIFY_SALT = "ferasha.email-verify"
PASSWORD_RESET_SALT = "ferasha.password-reset"  # noqa: S105 - salt, not a password

EMAIL_VERIFY_MAX_AGE = 60 * 60 * 48      # 48 hours
PASSWORD_RESET_MAX_AGE = 60 * 60         # 1 hour - shorter; it is more dangerous


class TokenInvalid(Exception):
    """Raised when a token is malformed, expired, or already consumed."""


def _fingerprint(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _email_state(user) -> str:
    return _fingerprint(
        str(user.pk),
        user.email,
        user.email_verified_at.isoformat() if user.email_verified_at else "unverified",
    )


def _password_state(user) -> str:
    # The password hash changes on reset, which invalidates any outstanding
    # token automatically.
    return _fingerprint(str(user.pk), user.password, str(user.last_login))


def make_email_verification_token(user) -> str:
    signer = TimestampSigner(salt=EMAIL_VERIFY_SALT)
    return signer.sign(f"{user.pk}:{_email_state(user)}")


def read_email_verification_token(token: str, user_model) -> object:
    signer = TimestampSigner(salt=EMAIL_VERIFY_SALT)
    try:
        payload = signer.unsign(token, max_age=EMAIL_VERIFY_MAX_AGE)
    except SignatureExpired as exc:
        raise TokenInvalid("This verification link has expired.") from exc
    except BadSignature as exc:
        raise TokenInvalid("This verification link is not valid.") from exc

    user_id, _, state = payload.partition(":")
    user = user_model.objects.filter(pk=user_id).first()
    if user is None:
        raise TokenInvalid("This verification link is not valid.")
    if _email_state(user) != state:
        # Already verified, or the email changed after the link was issued.
        raise TokenInvalid("This verification link has already been used.")
    return user


def make_password_reset_token(user) -> str:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    return signer.sign(f"{user.pk}:{_password_state(user)}")


def read_password_reset_token(token: str, user_model) -> object:
    signer = TimestampSigner(salt=PASSWORD_RESET_SALT)
    try:
        payload = signer.unsign(token, max_age=PASSWORD_RESET_MAX_AGE)
    except SignatureExpired as exc:
        raise TokenInvalid("This reset link has expired. Please request a new one.") from exc
    except BadSignature as exc:
        raise TokenInvalid("This reset link is not valid.") from exc

    user_id, _, state = payload.partition(":")
    user = user_model.objects.filter(pk=user_id).first()
    if user is None:
        raise TokenInvalid("This reset link is not valid.")
    if _password_state(user) != state:
        raise TokenInvalid("This reset link has already been used.")
    return user
