from __future__ import annotations

from django.apps import AppConfig


class TailoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tailoring"
    label = "tailoring"
    verbose_name = "Bespoke Tailoring"
