from __future__ import annotations

from django.apps import AppConfig


class TaxesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.taxes"
    label = "taxes"
    verbose_name = "GST Tax Engine"
