"""Grid cards get the primary photo and a second angle - approved photos only."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.catalog.models import ProductImage
from tests.factories import make_asset, make_product, make_variant

pytestmark = pytest.mark.django_db

PRODUCTS = reverse("catalog:product-list")


def photo(product, order, *, primary=False, approved=True, alt="Front"):
    asset = make_asset(derivative=SimpleUploadedFile(f"p{order}.jpg", b"blurred"))
    if approved:
        asset.mark_approved(faces=1, blur_verified=True)
    return ProductImage.objects.create(product=product, asset=asset, display_order=order, is_primary=primary, alt_text=alt)


def card(client):
    return client.get(PRODUCTS).json()["results"][0]


def test_primary_and_second_angle(api_client):
    product = make_product()
    make_variant(product=product)
    photo(product, 2, alt="Back")
    photo(product, 1, primary=True, alt="Front")

    data = card(api_client)

    assert data["primary_image"]["alt_text"] == "Front"
    assert data["secondary_image"]["alt_text"] == "Back"


def test_no_second_angle_with_one_photo(api_client):
    product = make_product()
    make_variant(product=product)
    photo(product, 1, primary=True)

    assert card(api_client)["secondary_image"] is None


def test_an_unapproved_photo_is_never_the_second_angle(api_client):
    product = make_product()
    make_variant(product=product)
    photo(product, 1, primary=True)
    photo(product, 2, approved=False, alt="Unblurred")

    assert card(api_client)["secondary_image"] is None
