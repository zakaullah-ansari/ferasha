from __future__ import annotations

import logging
from typing import Any, TypedDict
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status

from apps.cart.models import Cart
from apps.orders.models import Order, OrderLine, OrderStatus
from apps.orders.state_machine import OrderStateMachine
from apps.catalog.models import ProductVariant

logger = logging.getLogger(__name__)

class CheckoutState(TypedDict):
    address_validated: bool
    shipping_calculated: bool
    tax_quoted: bool
    order_placed: bool

class CheckoutService:
    """Coordinate the transition from Cart to Order.

    Follows a strict fail-closed pipeline:
    Address -> Shipping -> Tax -> Order.
    """

    @staticmethod
    def validate_address(cart: Cart, address_data: dict) -> bool:
        """Ensure shipping address is valid and deliverable.
        In a real system, this would call a Google Maps or DHL API.
        """
        # Ensure required fields are present
        required = ["street", "city", "state", "pincode", "country"]
        return all(address_data.get(f) for f in required)

    @staticmethod
    def calculate_shipping(cart: Cart, address_data: dict) -> float:
        """Calculate shipping costs based on destination.
        Example: Free shipping for Mumbai (MH), flat rate elsewhere.
        """
        state = address_data.get("state", "").upper()
        if state == "MH":
            return 0.0
        return 150.0 # Flat rate for other Indian states

    @staticmethod
    def quote_final_tax(cart: Cart, address_data: dict) -> dict:
        """Generate the final tax snapshot for the order.
        Calls the tax engine to lock in the GST rate at this moment.
        """
        # This would call apps.taxes.services.TaxService.quote
        return {
            "total_tax": 500.0,
            "cgst": 250.0,
            "sgst": 250.0,
            "igst": 0.0,
            "regime": "standard"
        }

    @staticmethod
    def place_order(user, cart: Cart, address_data: dict, shipping_cost: float, tax_quote: dict) -> Order:
        """Atomic conversion of Cart items into a locked Order.

        Uses transaction.atomic to ensure that if any step fails (e.g. stock
        check), the entire operation is rolled back.
        """
        with transaction.atomic():
            # 1. Create the Order
            order = Order.objects.create(
                user=user,
                shipping_address=f"{address_data['street']}, {address_data['city']}, {address_data['state']} {address_data['pincode']}",
                shipping_cost=shipping_cost,
                status=OrderStatus.DRAFT
            )

            # 2. Convert CartItems to OrderLines (Price Snapshot)
            for item in cart.items.all():
                OrderLine.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    unit_price=item.variant.price
                )

            # 3. Mark Cart as inactive
            cart.is_active = False
            cart.save()

            # 4. Transition to PLACED
            OrderStateMachine.transition(order, OrderStatus.PLACED)

            return order
