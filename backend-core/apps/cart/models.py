from __future__ import annotations

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.catalog.models import ProductVariant

class Cart(models.Model):
    """A temporary collection of items intended for purchase.

    Carts are linked to a user if authenticated, otherwise they are
    tracked via a session key for guest users.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts"
    )
    session_key = models.CharField(
        max_length=128,
        db_index=True,
        null=True,
        blank=True,
        help_text=_("Used to track guest carts before authentication.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        # Ensure a user has only one active cart at a time.
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="unique_active_user_cart"
            )
        ]

    def __str__(self) -> str:
        owner = self.user if self.user else f"Guest({self.session_key})"
        return f"Cart {self.id} - {owner}"


class CartItem(models.Model):
    """A specific product variant and its quantity within a cart."""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        # Prevent duplicate rows for the same variant in one cart.
        unique_together = ("cart", "variant")

    def __str__(self) -> str:
        return f"{self.variant.sku} x {self.quantity} (Cart {self.cart_id})"
