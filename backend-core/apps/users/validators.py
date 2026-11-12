"""Password validators beyond Django's built-ins."""

from __future__ import annotations

import hashlib
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class PwnedPasswordValidator:
    """Refuse passwords that appear in known data breaches (Have I Been Pwned).

    k-anonymity: only the first 5 hex characters of the password's SHA-1 are
    sent; the service returns every breached suffix under that prefix and the
    match happens here. ``Add-Padding`` makes every response a similar size,
    so the prefix cannot be guessed from traffic either.

    Fails open: if the service is slow or down, the password is accepted, so
    an outage elsewhere never blocks a sign-up. Turned off with
    ``PWNED_PASSWORDS_CHECK = False``.
    """

    endpoint = "https://api.pwnedpasswords.com/range/"
    timeout_seconds = 2

    def validate(self, password: str, user=None) -> None:
        if not getattr(settings, "PWNED_PASSWORDS_CHECK", True):
            return
        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # noqa: S324 - the API's format
        prefix, suffix = digest[:5], digest[5:]
        try:
            body = self._range(prefix)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("Breached-password check skipped: %s", exc)
            return
        for line in body.splitlines():
            candidate, _sep, count = line.strip().partition(":")
            if candidate == suffix and count.strip().isdigit() and int(count) > 0:
                raise ValidationError(
                    _(
                        "This password has appeared in a data breach elsewhere, so it is "
                        "easy to guess. Please choose a different one."
                    ),
                    code="password_breached",
                )

    def _range(self, prefix: str) -> str:
        """Breached suffixes for a hash prefix. The single network seam."""
        request = urllib.request.Request(  # noqa: S310 - fixed https endpoint
            f"{self.endpoint}{prefix}",
            headers={"Add-Padding": "true", "User-Agent": "ferasha-backend"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as reply:  # noqa: S310
            return reply.read().decode("utf-8")

    def get_help_text(self) -> str:
        return _("Your password must not be one that has appeared in a known data breach.")
