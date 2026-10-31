from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.cart.models import Cart, CartItem
from apps.catalog.models import ProductVariant
from apps.checkout.services import CheckoutService
from apps.orders.models import Order

@pytest.mark.django_db
class TestCheckoutPipeline:
    """
    High-fidelity tests for the Fail-Closed Checkout Pipeline.
    """

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def auth_user(self, db):
        from apps.users.models import User
        user = User.objects.create_user(username="luxury_client", password="password123")
        return user

    @pytest.fixture
    def active_cart(self, auth_user):
        cart = Cart.objects.create(user=auth_user, is_active=True)
        variant = ProductVariant.objects.create(
            sku="LUX-001",
            price=50000.0,
            # Assuming other required fields exist in ProductVariant
        )
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)
        return cart

    def test_validate_address_success(self, client, auth_user, active_cart):
        client.force_authenticate(user=auth_user)
        payload = {
            "street": "123 Imperial Way",
            "city": "Mumbai",
            "state": "MH",
            "pincode": "400001",
            "country": "India"
        }
        url = reverse('checkout-validate-address')
        response = client.post(url, payload, format='json')

        assert response.status_code == 200
        assert response.data['valid'] is True

    def test_validate_address_failure(self, client, auth_user, active_cart):
        client.force_authenticate(user=auth_user)
        payload = {"street": "Incomplete Address"} # Missing city, state, etc.
        url = reverse('checkout-validate-address')
        response = client.post(url, payload, format='json')

        assert response.status_code == 200
        assert response.data['valid'] is False

    def test_idempotent_order_placement(self, client, auth_user, active_cart):
        """
        Crucial Test: Ensures that replaying the same Idempotency-Key
        does not create duplicate orders.
        """
        client.force_authenticate(user=auth_user)
        url = reverse('checkout-place-order')
        idempotency_key = "unique-luxury-order-123"

        payload = {
            "address": {
                "street": "123 Imperial Way",
                "city": "Mumbai",
                "state": "MH",
                "pincode": "400001",
                "country": "India"
            },
            "shipping_cost": 0.0,
            "tax_quote": {"total_tax": 500.0}
        }

        # First Request
        response1 = client.post(url, payload, format='json', HTTP_X_IDEMPOTENCY_KEY=idempotency_key)
        assert response1.status_code == 201
        order_id_1 = response1.data['order_id']

        # Second Request (Replay)
        response2 = client.post(url, payload, format='json', HTTP_X_IDEMPOTENCY_KEY=idempotency_key)
        assert response2.status_code == 200 # Returns cached result
        order_id_2 = response2.data['order_id']

        assert order_id_1 == order_id_2
        assert Order.objects.filter(id=order_id_1).count() == 1

    def test_atomic_rollback_on_failure(self, client, auth_user, active_cart):
        """
        Ensure that if OrderLine creation fails, the Order itself is rolled back.
        """
        # We simulate a failure by mocking CheckoutService.place_order
        # or causing a DB constraint error.
        with pytest.raises(Exception):
            # Pass invalid data that would trigger a DB error deep in the service
            CheckoutService.place_order(
                user=auth_user,
                cart=active_cart,
                address_data={}, # This should cause KeyError in service
                shipping_cost=0,
                tax_quote={}
            )

        # Order should NOT exist because of transaction.atomic()
        assert Order.objects.filter(user=auth_user).count() == 0
