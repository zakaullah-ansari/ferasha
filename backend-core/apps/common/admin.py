"""Shared admin building blocks."""

from __future__ import annotations

from unfold.admin import ModelAdmin, StackedInline, TabularInline


class _NoWrites:
    """Records the system writes and people must never edit: view only."""

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class ReadOnlyAdmin(_NoWrites, ModelAdmin):
    """Ledgers and audit trails: payments, webhook events, order history."""


class ReadOnlyTabularInline(_NoWrites, TabularInline):
    extra = 0
    show_change_link = False


class ReadOnlyStackedInline(_NoWrites, StackedInline):
    extra = 0
