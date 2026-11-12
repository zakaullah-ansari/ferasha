"""A customer's own data: download it, or delete the account.

Required by the DPDP Act 2023 (a right to access, s.11, and to erasure,
s.12) and simply expected of a shop that holds measurements and addresses.

Deletion erases everything the shop does not have to keep, and keeps only
what the law requires. Invoices must be retained for years under GST
(CGST Act s.36), so an order, with the name and address frozen on it at
placement, outlives the account. That is why ``Order.customer`` is PROTECT
and why an account with orders is anonymised rather than removed: the
invoices keep pointing at a row that no longer says who it was.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.media_assets.models import MediaAsset
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import CustomerOrderEventSerializer, OrderLineSerializer
from apps.reviews.models import Review
from apps.tailoring.models import BespokeFitProfile
from apps.tailoring.serializers import FitProfileSerializer

from .serializers import AddressSerializer, revoke_all_refresh_tokens

logger = logging.getLogger(__name__)

#: Orders awaiting payment (the payment window may be open right now), being
#: made, on their way, or being returned. Deleting the account mid-order would leave the customer unable
#: to track, receive updates for, or return it, so deletion waits.
IN_PROGRESS = frozenset(
    {
        OrderStatus.PLACED,
        OrderStatus.PAYMENT_CONFIRMED,
        OrderStatus.IN_ATELIER,
        OrderStatus.MEASUREMENT_REVIEW,
        OrderStatus.STITCHING,
        OrderStatus.QUALITY_CHECK,
        OrderStatus.PACKED,
        OrderStatus.SHIPPED,
        OrderStatus.RETURN_REQUESTED,
    }
)

#: Where an anonymised account's email points: ``.invalid`` is reserved
#: (RFC 2606), so nothing can ever be delivered to it, and the real address
#: is free to register again.
ERASED_EMAIL_DOMAIN = "deleted.invalid"
ERASED_NAME = "Deleted customer"

#: Order fields a customer may see about their own order (no internal notes).
ORDER_FIELDS = (
    "order_number", "status", "currency", "shipping_address", "billing_address",
    "customer_gstin", "customer_notes", "subtotal", "discount_total", "shipping_charge",
    "tax_total", "grand_total", "placed_at", "delivered_at", "created_at",
)


class AccountDeletionBlocked(Exception):
    """The account has orders still in progress; ``order_numbers`` says which."""

    def __init__(self, order_numbers: list[str]):
        self.order_numbers = order_numbers
        super().__init__(", ".join(order_numbers))


@dataclass(frozen=True)
class DeletionOutcome:
    #: "deleted": nothing was left to keep. "anonymised": orders are kept for
    #: the tax records, attached to an account that no longer identifies anyone.
    kind: Literal["deleted", "anonymised"]


def orders_in_progress(user) -> list[str]:
    return list(
        Order.objects.filter(customer=user, status__in=IN_PROGRESS)
        .order_by("created_at")
        .values_list("order_number", flat=True)
    )


# -- Export -----------------------------------------------------------------


def export_account_data(user) -> dict[str, Any]:
    """Everything the shop holds about ``user``, as one JSON document.

    Built from the same serializers the account pages use, so the download
    never drifts from what the customer sees. Staff-only order fields (who
    acted, internal reasons) are left out, as on the order page.
    """
    orders = (
        Order.objects.filter(customer=user)
        .exclude(status=OrderStatus.DRAFT)
        .prefetch_related("lines__tailoring_spec", "events")
        .order_by("-created_at")
    )
    reviews = (
        Review.objects.filter(author=user).select_related("product").order_by("-created_at")
    )
    return {
        "exported_at": timezone.now().isoformat(),
        "profile": {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "preferences": user.preferences,
            "email_verified_at": _iso(user.email_verified_at),
            "accepted_terms_at": _iso(user.accepted_terms_at),
            "created_at": _iso(user.created_at),
            "last_login": _iso(user.last_login),
        },
        "addresses": AddressSerializer(user.addresses.all(), many=True).data,
        "linked_sign_in": [
            {
                "provider": link.provider,
                "email": link.email,
                "linked_at": _iso(link.created_at),
                "last_used_at": _iso(link.last_used_at),
            }
            for link in user.social_accounts.all()
        ],
        "fit_profiles": FitProfileSerializer(
            BespokeFitProfile.objects.filter(user=user), many=True
        ).data,
        "orders": [
            {
                **{field: _plain(getattr(order, field)) for field in ORDER_FIELDS},
                "lines": OrderLineSerializer(order.lines.all(), many=True).data,
                "timeline": CustomerOrderEventSerializer(order.events.all(), many=True).data,
            }
            for order in orders
        ],
        "reviews": [
            {
                "product": review.product.name,
                "rating": review.rating,
                "title": review.title,
                "body": review.body,
                "status": review.status,
                "created_at": _iso(review.created_at),
            }
            for review in reviews
        ],
    }


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _plain(value):
    """JSON-safe: dates as ISO strings, decimals as strings (exact money)."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is not None and not isinstance(value, str | int | float | bool | dict | list):
        return str(value)
    return value


# -- Deletion ---------------------------------------------------------------


@transaction.atomic
def delete_account(user) -> DeletionOutcome:
    """Erase ``user``'s personal data and close the account.

    Raises ``AccountDeletionBlocked`` while an order is in progress. The
    caller has already confirmed the password and that this is a customer
    account (staff accounts are closed by an admin, never self-service).
    """
    # Lock the row: two deletion requests at once must not interleave.
    user = type(user).objects.select_for_update().get(pk=user.pk)
    blocking = orders_in_progress(user)
    if blocking:
        raise AccountDeletionBlocked(blocking)

    user_id = user.pk
    revoke_all_refresh_tokens(user)

    # Customer content and saved details.
    assets = list(MediaAsset.objects.filter(review_photos__review__author=user).distinct())
    Review.objects.filter(author=user).delete()  # cascades to its photos
    _delete_assets(assets)
    user.addresses.all().delete()
    user.social_accounts.all().delete()
    Cart.objects.filter(user=user).delete()
    # Measurements and their history. What each order was actually cut from is
    # a separate frozen copy on the order (TailoringOrderSpec), kept with it.
    BespokeFitProfile.objects.filter(user=user).delete()
    # Checkouts never paid for: no invoice, nothing to keep.
    Order.objects.filter(
        customer=user, status=OrderStatus.DRAFT, payments__isnull=True
    ).delete()

    if not Order.objects.filter(customer=user).exists():
        user.delete()
        logger.info("Account %s deleted at the customer's request.", user_id)
        return DeletionOutcome("deleted")

    user.email = f"deleted-{user_id}@{ERASED_EMAIL_DOMAIN}"
    user.full_name = ERASED_NAME
    user.phone = ""
    user.preferences = {}
    user.email_verified_at = None
    user.phone_verified_at = None
    user.is_active = False
    user.set_unusable_password()
    user.save()
    logger.info("Account %s anonymised at the customer's request; orders kept.", user_id)
    return DeletionOutcome("anonymised")


def _delete_assets(assets: list[MediaAsset]) -> None:
    """Remove review photos: rows now, files once the deletion has committed
    (a rollback must not leave rows pointing at files that are gone)."""
    files = [f for asset in assets for f in (asset.original, asset.derivative) if f]
    for asset in assets:
        asset.delete()

    def remove_files() -> None:
        for field_file in files:
            try:
                field_file.storage.delete(field_file.name)
            except Exception:
                logger.exception("Could not remove %s after account deletion.", field_file.name)

    transaction.on_commit(remove_files)
