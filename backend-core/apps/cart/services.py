from __future__ import annotations

import logging
from typing import Optional
from django.db import transaction, F
from django.conf import settings
from apps.cart.models import Cart, CartItem
from apps.catalog.models import ProductVariant

logger = logging.getLogger(__name__)

class CartService:
    """Business logic for cart management.

    Encapsulates all cart mutations to ensure atomic updates and
    consistent state transitions.
    """

    @staticmethod
    def get_or_create_cart(user=None, session_key: Optional[str] = None) -> Cart:
        """Retrieve an active cart or create a new one.

        Priority:
        1. If user is authenticated, return their active cart.
        2. If session_key is provided, return that guest cart.
        3. Otherwise, create a new guest cart.
        """
        if user:
            cart = Cart.objects.filter(user=user, is_active=True).first()
            if cart:
                return cart

        if session_key:
            cart = Cart.objects.filter(session_key=session_key, is_active=True).first()
            if cart:
                return cart

        return Cart.objects.create(user=user, session_key=session_key)

    @staticmethod
    def add_item(cart: Cart, variant_id: str, quantity: int = 1) -> CartItem:
        """Atomically add or increment an item in the cart.

        Uses F() expressions to prevent race conditions during
        concurrent quantity updates.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        with transaction.atomic():
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant_id=variant_id,
                defaults={"quantity": quantity}
            )

            if not created:
                item.quantity = F("quantity") + quantity
                item.save()
                item.refresh_from_db()

        return item

    @staticmethod
    def update_quantity(cart: Cart, variant_id: str, quantity: int) -> CartItem:
        """Set a specific quantity for an item."""
        if quantity <= 0:
            return CartService.remove_item(cart, variant_id)

        with transaction.atomic():
            item = CartItem.objects.get(cart=cart, variant_id=variant_id)
            item.quantity = quantity
            item.save()

        return item

    @staticmethod
    def remove_item(cart: Cart, variant_id: str) -> bool:
        """Remove an item from the cart."""
        deleted, _ = CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
        return deleted > 0

    @staticmethod
    def clear_cart(cart: Cart) -> None:
        """Empty the cart and mark it as inactive."""
        CartItem.objects.filter(cart=cart).delete()
        cart.is_active = False
        cart.save()

    @staticmethod
    def merge_guest_cart(user, session_key: str) -> Cart:
        """Migrate items from a guest session to a registered user's cart.

        This is called during the authentication flow to ensure customers
        don't lose their items when they log in.
        """
        if not session_key:
            return CartService.get_or_create_cart(user=user)

        with transaction.atomic():
            guest_cart = Cart.objects.filter(session_key=session_key, is_active=True).first()
            user_cart = CartService.get_or_create_cart(user=user)

            if guest_cart and guest_cart != user_cart:
                # Migrate items
                items = CartItem.objects.filter(cart=guest_cart)
                for item in items:
                    CartService.add_item(user_cart, item.variant_id, item.quantity)

                # Deactivate guest cart
                guest_cart.is_active = False
                guest_cart.save()

            return user_cart
