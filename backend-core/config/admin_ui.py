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


#: Kausar Dezine Studio forest green (#307439 = oklch 50% 0.114 146.187) as the
#: primary ramp; 600 - the shade unfold paints buttons with - is the brand
#: value itself, which carries white text at 5.7:1. The neutral base is the
#: storefront's warm olive grey rather than unfold's default cool slate.
_PRIMARY_HUE = "146.187"
_BASE_HUE = "106.5"

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
        "base": {
            "50": f"oklch(98.8% .003 {_BASE_HUE})",
            "100": f"oklch(96.6% .005 {_BASE_HUE})",
            "200": f"oklch(93% .007 {_BASE_HUE})",
            "300": f"oklch(87% .009 {_BASE_HUE})",
            "400": f"oklch(70.7% .014 {_BASE_HUE})",
            "500": f"oklch(54% .02 {_BASE_HUE})",
            "600": f"oklch(44.5% .018 {_BASE_HUE})",
            "700": f"oklch(37% .015 {_BASE_HUE})",
            "800": f"oklch(26% .012 {_BASE_HUE})",
            "900": f"oklch(21% .01 {_BASE_HUE})",
            "950": f"oklch(15.3% .006 {_BASE_HUE})",
        },
        "primary": {
            "50": f"oklch(97.6% .018 {_PRIMARY_HUE})",
            "100": f"oklch(94.6% .036 {_PRIMARY_HUE})",
            "200": f"oklch(89.8% .065 {_PRIMARY_HUE})",
            "300": f"oklch(82.4% .098 {_PRIMARY_HUE})",
            "400": f"oklch(68% .12 {_PRIMARY_HUE})",
            "500": f"oklch(57% .124 {_PRIMARY_HUE})",
            "600": f"oklch(50% .114 {_PRIMARY_HUE})",
            "700": f"oklch(45% .105 {_PRIMARY_HUE})",
            "800": f"oklch(40% .095 {_PRIMARY_HUE})",
            "900": f"oklch(34% .08 {_PRIMARY_HUE})",
            "950": f"oklch(26% .062 {_PRIMARY_HUE})",
        },
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
