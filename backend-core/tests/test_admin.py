"""Back-office admin: every page renders, and order changes stay lawful.

The order admin is where staff can change the most money-relevant state, so
it gets the most scrutiny: only state-machine transitions, never via GET, only
with permission, always recorded under the staff member's name.
"""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.media_assets.models import MediaAsset
from apps.orders.models import OrderEvent, OrderStatus
from apps.reviews.models import Review, ReviewStatus
from tests.factories import make_user, make_vendor

pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser():
    return make_user(email="owner@example.com", is_staff=True, is_superuser=True)


@pytest.fixture
def admin_client(client, superuser):
    client.force_login(superuser)
    return client


def change_status_url(order) -> str:
    return reverse("admin:orders_order_change_status", args=[order.pk])


class TestEveryPageRenders:
    @pytest.mark.parametrize(
        "model",
        list(admin.site._registry),
        ids=lambda m: f"{m._meta.app_label}.{m._meta.model_name}",
    )
    def test_changelist(self, admin_client, model):
        url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
        assert admin_client.get(url).status_code == 200

    def test_dashboard(self, admin_client):
        assert admin_client.get(reverse("admin:index")).status_code == 200

    def test_order_detail_with_lines_tax_and_history(self, admin_client, placed_order):
        response = admin_client.get(reverse("admin:orders_order_change", args=[placed_order.pk]))

        assert response.status_code == 200
        body = response.content.decode()
        assert placed_order.order_number in body
        assert "Change status" in body

    def test_product_detail(self, admin_client, variant):
        url = reverse("admin:catalog_product_change", args=[variant.product.pk])
        assert admin_client.get(url).status_code == 200


class TestOrderStatusChange:
    def test_dialog_offers_only_lawful_moves(self, admin_client, placed_order):
        response = admin_client.get(change_status_url(placed_order), HTTP_HX_REQUEST="true")

        choices = {value for value, _ in response.context["form"].fields["status"].choices}
        assert choices == {OrderStatus.PAYMENT_CONFIRMED, OrderStatus.CANCELLED}

    def test_opening_the_dialog_changes_nothing(self, admin_client, placed_order):
        """A GET (e.g. a link or <img> on another site) must never move an order."""
        admin_client.get(change_status_url(placed_order), {"status": "cancelled"})

        placed_order.refresh_from_db()
        assert placed_order.status == OrderStatus.PLACED

    def test_change_is_applied_recorded_and_reloads_the_page(
        self, admin_client, superuser, placed_order
    ):
        response = admin_client.post(
            change_status_url(placed_order),
            {"_form_submitted": "1", "status": OrderStatus.PAYMENT_CONFIRMED, "reason": "Paid by UPI at shop"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("admin:orders_order_change", args=[placed_order.pk])
        placed_order.refresh_from_db()
        assert placed_order.status == OrderStatus.PAYMENT_CONFIRMED
        event = OrderEvent.objects.get(order=placed_order, to_status=OrderStatus.PAYMENT_CONFIRMED)
        assert event.actor == superuser
        assert event.reason == "Paid by UPI at shop"

    def test_cancelling_returns_stock(self, admin_client, placed_order, variant):
        admin_client.post(
            change_status_url(placed_order),
            {"_form_submitted": "1", "status": OrderStatus.CANCELLED},
            HTTP_HX_REQUEST="true",
        )

        variant.refresh_from_db()
        assert variant.stock_quantity == 5

    def test_an_unlawful_jump_is_refused(self, admin_client, placed_order):
        admin_client.post(
            change_status_url(placed_order),
            {"_form_submitted": "1", "status": OrderStatus.DELIVERED},
            HTTP_HX_REQUEST="true",
        )

        placed_order.refresh_from_db()
        assert placed_order.status == OrderStatus.PLACED

    def test_staff_without_change_permission_cannot_move_orders(self, client, placed_order):
        viewer = make_user(email="viewer@example.com", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_order"))
        client.force_login(viewer)

        response = client.post(
            change_status_url(placed_order),
            {"_form_submitted": "1", "status": OrderStatus.CANCELLED},
        )

        assert response.status_code == 403
        placed_order.refresh_from_db()
        assert placed_order.status == OrderStatus.PLACED

    def test_money_fields_cannot_be_edited(self, admin_client, placed_order):
        readonly = admin.site._registry[type(placed_order)].get_readonly_fields(None, placed_order)

        assert {"grand_total", "tax_total", "status", "customer"} <= set(readonly)
        assert "internal_notes" not in readonly

    def test_orders_cannot_be_added_or_deleted(self, admin_client, placed_order):
        assert admin_client.get(reverse("admin:orders_order_add")).status_code == 403
        delete = reverse("admin:orders_order_delete", args=[placed_order.pk])
        assert admin_client.get(delete).status_code == 403


class TestReviewModeration:
    def test_publish_records_the_moderator(self, admin_client, superuser, variant):
        review = Review.objects.create(
            product=variant.product, author=make_user(), rating=5, title="Beautiful work"
        )

        admin_client.post(
            reverse("admin:reviews_review_changelist"),
            {"action": "publish", "_selected_action": [str(review.pk)]},
        )

        review.refresh_from_db()
        assert review.status == ReviewStatus.PUBLISHED
        assert review.moderated_by == superuser

    def test_view_only_staff_cannot_moderate(self, client, variant):
        """Regression: actions without allowed_permissions run for anyone who can view the list."""
        viewer = make_user(email="review-viewer@example.com", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_review"))
        client.force_login(viewer)
        review = Review.objects.create(product=variant.product, author=make_user(), rating=1)

        for action_name in ("publish", "reject"):
            client.post(
                reverse("admin:reviews_review_changelist"),
                {"action": action_name, "_selected_action": [str(review.pk)]},
            )

        review.refresh_from_db()
        assert review.status == ReviewStatus.PENDING
        assert review.moderated_by is None


class TestImagePicker:
    def test_only_approved_images_are_offered(self, admin_client):
        vendor = make_vendor()

        def asset(**kw):
            return MediaAsset.objects.create(
                uploaded_by=vendor,
                original=SimpleUploadedFile("photo.jpg", b"bytes"),
                checksum="a" * 64,
                content_type="image/jpeg",
                byte_size=5,
                **kw,
            )

        approved = asset(derivative=SimpleUploadedFile("blurred.jpg", b"blurred"))
        approved.mark_approved(faces=1, blur_verified=True)
        pending = asset()

        response = admin_client.get(
            reverse("admin:autocomplete"),
            {"app_label": "catalog", "model_name": "productimage", "field_name": "asset", "term": ""},
        )

        offered = {row["id"] for row in response.json()["results"]}
        assert str(approved.pk) in offered
        assert str(pending.pk) not in offered


def test_logging_in_directly_at_the_admin_login_lands_on_the_dashboard(client, superuser):
    superuser.set_password("Correct-Horse-9182")
    superuser.save()

    response = client.post(
        reverse("admin:login"), {"username": superuser.email, "password": "Correct-Horse-9182"}
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("admin:index")
