"""Fit profiles: customers' measurements, view only.

These are personal body measurements. Staff can read them to cut a garment;
changes go through the customer (or a recorded atelier measurement) so the
revision history stays truthful.
"""

from __future__ import annotations

from django.contrib import admin

from apps.common.admin import ReadOnlyAdmin

from .models import BespokeFitProfile


@admin.register(BespokeFitProfile)
class BespokeFitProfileAdmin(ReadOnlyAdmin):
    list_display = ("label", "user", "garment_type", "measured_by", "verified_at", "is_default")
    list_filter = ("garment_type", "measured_by", "is_default")
    search_fields = ("label", "user__email", "user__full_name")
    list_select_related = ("user",)
