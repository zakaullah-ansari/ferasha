from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.utils.deprecation import warn_redundant

from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from .services import CartService

class CartViewSet(viewsets.ViewSet):
    """API for managing the shopping cart.

    Handles both authenticated users and guests via session keys.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_cart(self, request) -> Cart:
        """Retrieve the cart for the current user or session."""
        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key
        return CartService.get_or_create_cart(user=user, session_key=session_key)

    def list(self, request):
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def create(self, request):
        """Add an item to the cart.
        Payload: {"variant_id": "...", "quantity": 1}
        """
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))

        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_cart(request)
        try:
            CartService.add_item(cart, variant_id, quantity)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.list(request))

    @action(detail=False, methods=["post"])
    def update_item(self, request):
        """Update the quantity of a specific item."""
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))

        cart = self.get_cart(request)
        try:
            CartService.update_quantity(cart, variant_id, quantity)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.list(request))

    @action(detail=False, methods=["delete"], url_path="remove/(?P<variant_id>[^/.]+)")
    def remove_item(self, request, variant_id=None):
        """Remove an item from the cart."""
        cart = self.get_cart(request)
        if CartService.remove_item(cart, variant_id):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Item not found in cart."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """Empty the cart."""
        cart = self.get_cart(request)
        CartService.clear_cart(cart)
        return Response(status=status.HTTP_204_NO_CONTENT)
