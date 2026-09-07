"""Catalogue service functions.

Stock mutation lives here, not in a serializer or a view, because it is the one
operation in the catalogue that is genuinely concurrency-sensitive.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import F

from .models import ProductVariant


class InsufficientStock(Exception):
    """Raised when a stock decrement would drive the variant negative."""

    def __init__(self, sku: str, requested: int, available: int):
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {sku}: requested {requested}, available {available}."
        )


@transaction.atomic
def reserve_stock(variant_id, quantity: int) -> ProductVariant:
    """Atomically decrement stock.

    Uses a conditional UPDATE rather than read-modify-write. Two customers
    checking out the last lehenga simultaneously would both read
    ``stock_quantity == 1`` and both succeed under a naive implementation; the
    conditional update means exactly one wins and the other is told the truth.

    The database CheckConstraint on stock_quantity is the final backstop.
    """
    if quantity < 1:
        raise ValueError("quantity must be at least 1.")

    updated = ProductVariant.objects.filter(
        pk=variant_id, stock_quantity__gte=quantity
    ).update(stock_quantity=F("stock_quantity") - quantity)

    if not updated:
        variant = ProductVariant.objects.filter(pk=variant_id).only("sku", "stock_quantity").first()
        if variant is None:
            raise ProductVariant.DoesNotExist(f"No variant {variant_id}.")
        raise InsufficientStock(variant.sku, quantity, variant.stock_quantity)

    return ProductVariant.objects.get(pk=variant_id)


@transaction.atomic
def release_stock(variant_id, quantity: int) -> ProductVariant:
    """Return stock on cancellation or a failed payment."""
    if quantity < 1:
        raise ValueError("quantity must be at least 1.")
    ProductVariant.objects.filter(pk=variant_id).update(
        stock_quantity=F("stock_quantity") + quantity
    )
    return ProductVariant.objects.get(pk=variant_id)
