from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.catalog.models import ProductVariant


class Cart(models.Model):
    """A customer's bag. Guests keep theirs client-side until they sign in.

    Retired (``is_active=False``) rather than deleted at checkout, so the
    lines that became an order stay inspectable.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        constraints = [
            # One active bag per customer; checkout retires it.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="unique_active_user_cart",
            )
        ]

    def __str__(self) -> str:
        return f"Cart {self.pk} - {self.user}"


class CartItem(models.Model):
    """A product variant and its quantity within a cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="unique_variant_per_cart"),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="cartitem_quantity_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.variant.sku} x {self.quantity} (Cart {self.cart_id})"
