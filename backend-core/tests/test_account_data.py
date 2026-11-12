"""Download my data, delete my account (DPDP Act 2023 ss.11-12).

Deletion erases what the shop need not keep and keeps what tax law makes it
keep: an account with past orders is anonymised, not removed, so its
invoices survive without naming anyone.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.cart.models import Cart
from apps.media_assets.models import MediaAsset
from apps.orders.models import Order, OrderStatus
from apps.reviews.models import Review, ReviewPhoto
from apps.tailoring.models import BespokeFitProfile
from apps.users.account_data import ERASED_EMAIL_DOMAIN, ERASED_NAME
from apps.users.models import Address, SocialAccount
from tests.factories import make_asset, make_variant

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "Correct-Horse-9182"  # the conftest customer's password


def delete(client, password=PASSWORD):
    return client.post(reverse("users:account-delete"), {"password": password}, format="json")


@pytest.fixture
def saved_details(customer):
    """Everything a customer leaves behind: address, Google link, cart, measurements."""
    Address.objects.create(
        user=customer, recipient_name="Ayesha Khan", phone="+919820012345",
        line1="402 Imperial Heights", city="Mumbai", state_code="MH",
        postal_code="400001", country_code="IN",
    )
    SocialAccount.objects.create(
        user=customer, provider="google", subject="g-123", email=customer.email
    )
    Cart.objects.create(user=customer)
    BespokeFitProfile.objects.create(
        user=customer, label="My measurements",
        measurements={"bust": 36, "waist": 30, "hip": 38}, unit_system="inch",
    )
    return customer


def finish(order, status=OrderStatus.DELIVERED):
    Order.objects.filter(pk=order.pk).update(status=status)
    return order


class TestDeleteAccount:
    def test_without_orders_the_account_is_removed_entirely(self, auth_client, saved_details):
        user_id = saved_details.pk
        response = delete(auth_client)

        assert response.status_code == 200
        assert not User.objects.filter(pk=user_id).exists()
        assert not Address.objects.filter(user_id=user_id).exists()
        assert not SocialAccount.objects.filter(user_id=user_id).exists()
        assert not Cart.objects.filter(user_id=user_id).exists()
        assert not BespokeFitProfile.objects.filter(user_id=user_id).exists()

    def test_with_past_orders_the_account_is_anonymised_and_orders_kept(
        self, auth_client, saved_details, placed_order
    ):
        finish(placed_order)
        response = delete(auth_client)

        assert response.status_code == 200
        user = User.objects.get(pk=saved_details.pk)
        assert user.email == f"deleted-{user.pk}@{ERASED_EMAIL_DOMAIN}"
        assert user.full_name == ERASED_NAME
        assert user.phone == ""
        assert user.preferences == {}
        assert not user.is_active
        assert not user.has_usable_password()
        # The invoice record survives, still attached to the (now anonymous) row.
        assert Order.objects.filter(pk=placed_order.pk, customer=user).exists()
        assert not user.addresses.exists()
        assert not BespokeFitProfile.objects.filter(user=user).exists()

    def test_the_email_is_free_to_register_again(self, auth_client, customer, placed_order):
        finish(placed_order)
        delete(auth_client)
        auth_client.credentials()  # that session is over
        response = auth_client.post(
            reverse("users:register"),
            {
                "email": "ayesha@example.com", "password": "Fresh-Start-4471",
                "full_name": "Ayesha Khan", "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 201

    def test_unpaid_checkouts_are_erased_not_kept(self, auth_client, customer, placed_order):
        finish(placed_order, OrderStatus.DRAFT)
        delete(auth_client)
        assert not Order.objects.filter(pk=placed_order.pk).exists()
        assert not User.objects.filter(pk=customer.pk).exists()

    @pytest.mark.parametrize(
        "status",
        [
            OrderStatus.PLACED,  # awaiting payment: the gateway may be mid-capture
            OrderStatus.PAYMENT_CONFIRMED,
            OrderStatus.STITCHING,
            OrderStatus.SHIPPED,
            OrderStatus.RETURN_REQUESTED,
        ],
    )
    def test_waits_while_an_order_is_in_progress(self, auth_client, customer, placed_order, status):
        finish(placed_order, status)
        response = delete(auth_client)

        assert response.status_code == 409
        assert response.data["order_numbers"] == [placed_order.order_number]
        assert placed_order.order_number in response.data["detail"]
        assert User.objects.get(pk=customer.pk).is_active

    def test_needs_the_right_password(self, auth_client, customer):
        response = delete(auth_client, password="not-my-password")
        assert response.status_code == 400
        assert "password" in response.data
        assert User.objects.filter(pk=customer.pk).exists()

    def test_google_only_account_is_told_to_set_a_password_first(self, customer):
        from tests.conftest import _client_for

        customer.set_unusable_password()
        customer.save()
        response = delete(_client_for(customer), password="anything")
        assert response.status_code == 400
        assert "Forgot password" in str(response.data["password"])

    def test_staff_accounts_are_closed_by_an_admin(self, staff_user):
        from tests.conftest import _client_for

        response = delete(_client_for(staff_user), password="whatever")
        assert response.status_code == 403
        assert User.objects.filter(pk=staff_user.pk).exists()

    def test_requires_sign_in(self, api_client):
        assert delete(api_client).status_code == 401

    def test_signs_out_every_session(self, auth_client, customer, placed_order):
        finish(placed_order)
        refresh = RefreshToken.for_user(customer)
        delete(auth_client)

        token = OutstandingToken.objects.get(jti=refresh["jti"])
        assert hasattr(token, "blacklistedtoken")
        response = auth_client.post(
            reverse("users:token-refresh"), {"refresh": str(refresh)}, format="json"
        )
        assert response.status_code == 401

    def test_sends_a_confirmation_to_the_old_address(self, auth_client, customer):
        delete(auth_client)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["ayesha@example.com"]
        assert "deleted" in mail.outbox[0].subject

    def test_reviews_and_their_photo_files_are_erased(
        self, auth_client, customer, settings, tmp_path, django_capture_on_commit_callbacks
    ):
        settings.MEDIA_ROOT = tmp_path
        review = Review.objects.create(
            product=make_variant().product, author=customer, rating=5, title="Lovely"
        )
        asset = make_asset(uploaded_by=customer)
        ReviewPhoto.objects.create(review=review, asset=asset)
        stored = tmp_path / asset.original.name
        assert stored.exists()

        with django_capture_on_commit_callbacks(execute=True):
            response = delete(auth_client)

        assert response.status_code == 200
        assert not Review.objects.filter(pk=review.pk).exists()
        assert not MediaAsset.objects.filter(pk=asset.pk).exists()
        assert not stored.exists()


class TestExport:
    def test_contains_what_the_shop_holds(self, auth_client, saved_details, placed_order):
        finish(placed_order)
        response = auth_client.get(reverse("users:account-export"))

        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment; filename=")
        assert "no-store" in response["Cache-Control"]
        data = response.json()
        assert data["profile"]["email"] == "ayesha@example.com"
        assert data["profile"]["phone"] == "+919820012345"
        assert data["addresses"][0]["city"] == "Mumbai"
        assert data["linked_sign_in"][0]["provider"] == "google"
        assert data["fit_profiles"][0]["measurements"]["bust"] == 36
        assert data["orders"][0]["order_number"] == placed_order.order_number
        assert data["orders"][0]["lines"]

    def test_leaves_out_unpaid_checkouts_and_staff_notes(self, auth_client, customer, placed_order):
        finish(placed_order, OrderStatus.DRAFT)
        data = auth_client.get(reverse("users:account-export")).json()
        assert data["orders"] == []  # a draft is not an order yet

        finish(placed_order)
        data = auth_client.get(reverse("users:account-export")).json()
        for event in data["orders"][0]["timeline"]:
            assert "reason" not in event
            assert "actor_name" not in event

    def test_only_ever_the_signed_in_customer(self, other_client, customer, placed_order):
        finish(placed_order)
        data = other_client.get(reverse("users:account-export")).json()
        assert data["profile"]["email"] != "ayesha@example.com"
        assert data["orders"] == []

    def test_requires_sign_in(self, api_client):
        assert api_client.get(reverse("users:account-export")).status_code == 401
