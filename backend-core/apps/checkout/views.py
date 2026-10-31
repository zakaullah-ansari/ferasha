from __future__ import annotations

import logging
from typing import Any
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser

from .services import CheckoutService
from apps.cart.models import Cart
from apps.orders.models import Order

logger = logging.getLogger(__name__)

class CheckoutViewSet(viewsets.ViewSet):
    """
    The Checkout Pipeline.
    Coordinates the transition from a Cart to a locked Order.

    Flow:
    1. POST /validate-address/ -> returns validity
    2. POST /calculate-shipping/ -> returns cost
    3. POST /quote-tax/ -> returns final tax snapshot
    4. POST /place-order/ -> creates Order and clears Cart
    """
    permission_classes = [IsAuthenticated]

    def _get_active_cart(self, request) -> Cart:
        """Retrieve the active cart for the authenticated user."""
        cart = Cart.objects.filter(user=request.user, is_active=True).first()
        if not cart:
            return None
        return cart

    @action(detail=False, methods=["post"])
    def validate_address(self, request):
        """Step 1: Validate the shipping address."""
        address_data = request.data
        cart = self._get_active_cart(request)
        if not cart:
            return Response({"detail": "No active cart found."}, status=status.HTTP_400_BAD_REQUEST)

        is_valid = CheckoutService.validate_address(cart, address_data)
        return Response({"valid": is_valid}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def calculate_shipping(self, request):
        """Step 2: Calculate shipping costs based on address."""
        address_data = request.data
        cart = self._get_active_cart(request)
        if not cart:
            return Response({"detail": "No active cart found."}, status=status.HTTP_400_BAD_REQUEST)

        cost = CheckoutService.calculate_shipping(cart, address_data)
        return Response({"shipping_cost": cost}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def quote_tax(self, request):
        """Step 3: Lock in the final tax quote."""
        address_data = request.data
        cart = self._get_active_cart(request)
        if not cart:
            return Response({"detail": "No active cart found."}, status=status.HTTP_400_BAD_REQUEST)

        tax_quote = CheckoutService.quote_final_tax(cart, address_data)
        return Response(tax_quote, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def place_order(self, request):
        """Step 4: Convert Cart to Order.
        Expects: address_data, shipping_cost, tax_quote.
        """
        data = request.data
        address_data = data.get("address")
        shipping_cost = data.get("shipping_cost")
        tax_quote = data.get("tax_quote")

        if not all([address_data, shipping_cost, tax_quote]):
            return Response(
                {"detail": "Missing required checkout data (address, shipping, or tax)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = self._get_active_cart(request)
        if not cart:
            return Response({"detail": "No active cart found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = CheckoutService.place_order(
                user=request.user,
                cart=cart,
                address_data=address_data,
                shipping_cost=float(shipping_cost),
                tax_quote=tax_quote
            )
            return Response({
                "order_id": order.id,
                "status": order.status,
                "detail": "Order placed successfully."
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error("Order placement failed: %s", str(exc))
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
