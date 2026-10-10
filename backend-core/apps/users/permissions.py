"""Reusable object-level permissions.

Default-deny is configured globally in ``REST_FRAMEWORK``; these classes narrow
access further. Object ownership is enforced here rather than in views so the
rule cannot be forgotten when a new viewset is added.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import UserRole


def _owner_of(obj: Any) -> Any:
    """Best-effort resolution of the owning user for an arbitrary object."""
    for attr in ("user", "owner", "customer"):
        if hasattr(obj, attr):
            return getattr(obj, attr)
    return obj if hasattr(obj, "email") else None


class IsOwnerOrBackOffice(BasePermission):
    """Allow access only to the owning user, or to staff/admin roles.

    Critical for bespoke fit profiles: a customer's body measurements must
    never be readable by another customer.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_back_office:
            return True
        return _owner_of(obj) == user


class IsBackOffice(BasePermission):
    message = "Back-office access is required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_back_office)


class IsVendorOrBackOffice(BasePermission):
    message = "Vendor access is required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == UserRole.VENDOR or user.is_back_office)
        )


class IsTailorOrBackOffice(BasePermission):
    message = "Atelier access is required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role in {UserRole.TAILOR, UserRole.STYLIST} or user.is_back_office)
        )


class ReadOnlyOrBackOffice(BasePermission):
    """Public catalogue reads; mutations restricted to back office."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_back_office)
