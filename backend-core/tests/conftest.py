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


@pytest.fixture
def auth_client(api_client, customer):
    from apps.users.serializers import FerashaTokenObtainPairSerializer

    token = FerashaTokenObtainPairSerializer.get_token(customer)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client
