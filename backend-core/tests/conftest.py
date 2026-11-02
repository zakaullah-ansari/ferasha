"""Shared pytest fixtures for backend-core."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def customer(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="ayesha@example.com",
        password="Correct-Horse-9182",
        full_name="Ayesha Khan",
        phone="+919820012345",
    )


@pytest.fixture
def other_customer(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="zainab@example.com",
        password="Correct-Horse-9182",
        full_name="Zainab Ali",
    )


@pytest.fixture
def staff_user(db):
    from django.contrib.auth import get_user_model

    from apps.users.models import UserRole

    return get_user_model().objects.create_user(
        email="ops@ferasha.com",
        password="Correct-Horse-9182",
        full_name="Ops Desk",
        role=UserRole.STAFF,
        is_staff=True,
    )


def _client_for(user):
    from rest_framework.test import APIClient

    from apps.users.serializers import FerashaTokenObtainPairSerializer

    client = APIClient()
    token = FerashaTokenObtainPairSerializer.get_token(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def auth_client(api_client, customer):
    from apps.users.serializers import FerashaTokenObtainPairSerializer

    token = FerashaTokenObtainPairSerializer.get_token(customer)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.fixture
def other_client(other_customer):
    return _client_for(other_customer)


# --- Commerce ---------------------------------------------------------------
# One Rs.12,000 suit (HSN 6204: the 18% GST 2.0 slab), five in stock.


@pytest.fixture
def variant(db):
    from tests.factories import make_variant

    return make_variant(stock_quantity=5)


@pytest.fixture
def filled_cart(customer, variant):
    from apps.cart import services as cart_services

    cart = cart_services.get_active_cart(customer)
    cart_services.add_item(cart, variant.pk, 1)
    return cart


#: Valid inline delivery addresses. MH is Ferasha's home state.
MUMBAI = {
    "recipient_name": "Ayesha Khan",
    "phone": "+919820012345",
    "line1": "402 Imperial Heights",
    "city": "Mumbai",
    "state_code": "MH",
    "postal_code": "400001",
    "country_code": "IN",
}
BENGALURU = {**MUMBAI, "city": "Bengaluru", "state_code": "KA", "postal_code": "560001"}


@pytest.fixture
def placed_order(customer, filled_cart):
    from apps.checkout import services as checkout_services

    return checkout_services.place_order(customer, dict(MUMBAI))
