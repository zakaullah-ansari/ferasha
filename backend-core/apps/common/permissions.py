"""Object-level permission classes shared across the API.

DRF is configured default-deny (``IsAuthenticated`` globally); these classes
narrow access further. Ownership is enforced here rather than inside each view
so the rule cannot be forgotten when a new viewset is added.

A note on 404 vs 403: querysets are scoped to the requesting principal, so a
foreign object is *absent* rather than *forbidden*. A 403 would confirm that
the resource exists, which is an enumeration oracle. Body measurements are
sensitive personal data under the DPDP Act 2023; that leak is not acceptable.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.models import UserRole


def resolve_owner(obj: Any) -> Any:
    """Best-effort resolution of the user who owns an arbitrary object."""
    for attr in ("user", "owner", "customer", "author", "uploaded_by"):
        if hasattr(obj, attr):
            return getattr(obj, attr)
    # A User instance owns itself.
    return obj if hasattr(obj, "email") else None


class IsOwnerOrBackOffice(BasePermission):
    """Only the owning user, or staff/admin, may touch the object."""

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_back_office:
            return True
        return resolve_owner(obj) == user


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

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_back_office:
            return True
        vendor = getattr(obj, "vendor", None)
        return vendor == user


class IsAtelierOrBackOffice(BasePermission):
    """Tailors and stylists working the atelier queue."""

    message = "Atelier access is required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.role in {UserRole.TAILOR, UserRole.STYLIST}
                or user.is_back_office
            )
        )


class PublicReadBackOfficeWrite(BasePermission):
    """Anonymous catalogue reads; mutations restricted to the back office."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_back_office)


class PublicReadVendorWrite(BasePermission):
    """Anonymous reads; vendors may write, but only their own records."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == UserRole.VENDOR or user.is_back_office)
        )

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if user.is_back_office:
            return True
        return getattr(obj, "vendor", None) == user


class IsAuthenticatedAndVerified(BasePermission):
    """Authenticated with a verified email address.

    Reserved for actions with real-world consequences - placing an order,
    submitting a review - where an unverified address is a spam vector.
    """

    message = "Please verify your email address to continue."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.email_is_verified)
