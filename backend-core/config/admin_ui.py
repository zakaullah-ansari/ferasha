"""Admin (django-unfold) look and navigation for the Ferasha back office.

Kept out of settings.py so the settings module stays declarative and this can
import URL helpers lazily.
"""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def environment_callback(request) -> list[str]:
    """Badge in the admin header, so a test site is never mistaken for live."""
    return ["Development", "warning"] if settings.DEBUG else ["Production", "danger"]


def _can(permission: str):
    """Hide a sidebar link from staff who could not open it anyway."""
    return lambda request: request.user.has_perm(permission)


def _item(title, icon: str, app_label: str, model: str) -> dict:
    return {
        "title": title,
        "icon": icon,
        "link": reverse_lazy(f"admin:{app_label}_{model}_changelist"),
        "permission": _can(f"{app_label}.view_{model}"),
    }


#: The storefront's colours, copied verbatim from frontend/app/globals.css
#: (:root --primary and --foreground). That file is the single source of truth
#: - it is what browsers paint and what the contrast tests check - and
#: frontend/tests/admin-theme-sync.test.ts fails if these two drift from it.
#: Every admin shade below is derived from them, never typed by hand.
STOREFRONT_PRIMARY = "oklch(0.5 0.114 146.187)"  # Kausar Dezine Studio green
STOREFRONT_FOREGROUND = "oklch(0.153 0.006 107.1)"  # warm olive ink

_STEPS = ("50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950")


def _lch(oklch: str) -> tuple[float, float, float]:
    lightness, chroma, hue = oklch.removeprefix("oklch(").removesuffix(")").split()
    return float(lightness), float(chroma), float(hue)


def _primary_ramp(oklch: str) -> dict[str, str]:
    """Tints and shades around the brand colour, which sits at 600 exactly:
    600 is the shade unfold paints buttons with, so they are the storefront's
    own primary and carry white text at the same contrast (5.7:1)."""
    lightness, chroma, hue = _lch(oklch)
    lightnesses = (0.976, 0.946, 0.898, 0.824, 0.68, 0.57, lightness, 0.45, 0.40, 0.34, 0.26)
    # Chroma relative to the brand: muted tints, full colour in the mid-range.
    chroma_scale = (0.16, 0.32, 0.57, 0.86, 1.05, 1.09, 1.0, 0.92, 0.83, 0.70, 0.54)
    return {
        step: f"oklch({l_ * 100:.1f}% {chroma * k:.3f} {hue})"
        for step, l_, k in zip(_STEPS, lightnesses, chroma_scale, strict=True)
    }


def _neutral_ramp(oklch: str) -> dict[str, str]:
    """Greys carrying the storefront ink's warm olive hue instead of
    unfold's default cool slate; 950 is the ink itself."""
    lightness, _chroma, hue = _lch(oklch)
    lightnesses = (0.988, 0.966, 0.93, 0.87, 0.707, 0.54, 0.445, 0.37, 0.26, 0.21, lightness)
    chromas = (0.003, 0.005, 0.007, 0.009, 0.014, 0.02, 0.018, 0.015, 0.012, 0.01, 0.006)
    return {
        step: f"oklch({l_ * 100:.1f}% {c:.3f} {hue})"
        for step, l_, c in zip(_STEPS, lightnesses, chromas, strict=True)
    }

UNFOLD = {
    "SITE_TITLE": "Ferasha Atelier",
    "SITE_HEADER": "Ferasha",
    "SITE_SUBHEADER": _("by Kausar Dezine Studio"),
    "SITE_SYMBOL": "checkroom",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "ENVIRONMENT": "config.admin_ui.environment_callback",
    "COLORS": {
        "base": _neutral_ramp(STOREFRONT_FOREGROUND),
        "primary": _primary_ramp(STOREFRONT_PRIMARY),
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Sales"),
                "items": [
                    _item(_("Orders"), "shopping_bag", "orders", "order"),
                    _item(_("Payments"), "payments", "payments", "payment"),
                ],
            },
            {
                "title": _("Catalogue"),
                "items": [
                    _item(_("Products"), "checkroom", "catalog", "product"),
                    _item(_("Stock"), "inventory_2", "catalog", "productvariant"),
                    _item(_("Categories"), "category", "catalog", "category"),
                    _item(_("Images"), "photo_library", "media_assets", "mediaasset"),
                ],
            },
            {
                "title": _("Customers"),
                "items": [
                    _item(_("Customers"), "group", "users", "user"),
                    _item(_("Addresses"), "home_pin", "users", "address"),
                    _item(_("Reviews"), "reviews", "reviews", "review"),
                    _item(_("Fit profiles"), "straighten", "tailoring", "bespokefitprofile"),
                ],
            },
            {
                "title": _("System"),
                "collapsible": True,
                "items": [
                    _item(_("Payment webhooks"), "webhook", "payments", "paymentwebhookevent"),
                    _item(_("Staff groups"), "admin_panel_settings", "auth", "group"),
                ],
            },
        ],
    },
}
