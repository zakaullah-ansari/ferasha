"""Cart mutations.

The server cart belongs to an authenticated customer. Guests keep their basket
client-side and hand it over through ``merge_items`` at sign-in: the API
authenticates with JWTs, so there is no session cookie to key a server-side
guest cart on.

Every mutation validates the variant is purchasable and clamps against stock
here, so the cart can never hold something checkout is bound to refuse.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db import IntegrityError, transaction

from apps.catalog.enums import ProductStatus
from apps.catalog.models import ProductVariant

from .models import Cart, CartItem

#: Upper bound per line. A luxury basket with 50 of one lehenga is an error or
#: abuse, never a real order; refusing it keeps stock locks short at checkout.
MAX_QUANTITY_PER_LINE = 10


class CartError(ValueError):
    """A cart mutation the customer can correct (bad variant, no stock)."""


def _purchasable_variant(variant_id: Any) -> ProductVariant:
    try:
        variant = ProductVariant.objects.select_related("product").get(pk=variant_id)
    except (ProductVariant.DoesNotExist, ValueError, TypeError) as exc:
        # ValueError/TypeError: a malformed UUID is "not found", not a 500.
        raise CartError("That item is not available.") from exc
    if not variant.is_active or variant.product.status != ProductStatus.ACTIVE:
        raise CartError("That item is no longer available.")
    return variant


def _validated_quantity(quantity: Any) -> int:
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise CartError("Quantity must be a whole number.") from exc
    if value < 1:
        raise CartError("Quantity must be at least 1.")
    return value


def _clamp_to_stock(variant: ProductVariant, quantity: int) -> int:
    available = min(variant.stock_quantity, MAX_QUANTITY_PER_LINE)
    if available < 1:
        raise CartError(f"{variant.product.name} ({variant.size}) is out of stock.")
    return min(quantity, available)


def get_active_cart(user) -> Cart:
    """The customer's single active cart, created on first use.

    ``unique_active_user_cart`` makes a concurrent double-create fail in the
    database; the loser re-reads the winner's row instead of erroring.
    """
    cart = Cart.objects.filter(user=user, is_active=True).first()
    if cart is not None:
        return cart
    try:
        with transaction.atomic():
            return Cart.objects.create(user=user)
    except IntegrityError:
        return Cart.objects.get(user=user, is_active=True)


@transaction.atomic
def add_item(cart: Cart, variant_id: Any, quantity: Any = 1) -> CartItem:
    """Add a variant, or increase its quantity if already in the cart."""
    quantity = _validated_quantity(quantity)
    variant = _purchasable_variant(variant_id)
    # Lock the line so two concurrent adds sum rather than overwrite.
    item = CartItem.objects.select_for_update().filter(cart=cart, variant=variant).first()
    current = item.quantity if item else 0
    target = _clamp_to_stock(variant, current + quantity)
    if item is None:
        return CartItem.objects.create(cart=cart, variant=variant, quantity=target)
    item.quantity = target
    item.save(update_fields=["quantity", "updated_at"])
    return item


@transaction.atomic
def set_quantity(cart: Cart, variant_id: Any, quantity: Any) -> CartItem | None:
    """Set an exact quantity. Zero removes the line and returns ``None``."""
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise CartError("Quantity must be a whole number.") from exc
    if value <= 0:
        remove_item(cart, variant_id)
        return None
    item = (
        CartItem.objects.select_for_update()
        .select_related("variant__product")
        .filter(cart=cart, variant_id=variant_id)
        .first()
    )
    if item is None:
        raise CartError("That item is not in your bag.")
    item.quantity = _clamp_to_stock(item.variant, value)
    item.save(update_fields=["quantity", "updated_at"])
    return item


def remove_item(cart: Cart, variant_id: Any) -> bool:
    try:
        deleted, _ = CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
    except (ValueError, TypeError):
        return False
    return deleted > 0


def clear(cart: Cart) -> None:
    cart.items.all().delete()


@transaction.atomic
def merge_items(cart: Cart, items: Iterable[dict[str, Any]]) -> list[str]:
    """Fold a guest basket into the customer's cart at sign-in.

    Unavailable lines are skipped rather than failing the whole merge - losing
    one sold-out item is better than losing the bag. Returns the skipped ids so
    the storefront can tell the customer.
    """
    skipped: list[str] = []
    for entry in items:
        variant_id = entry.get("variant_id")
        try:
            add_item(cart, variant_id, entry.get("quantity", 1))
        except CartError:
            skipped.append(str(variant_id))
    return skipped
