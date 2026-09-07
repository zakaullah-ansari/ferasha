"""Authorisation matrix: every role x every endpoint x own-vs-foreign resource.

This is the highest-value test suite in the project. Body measurements are
sensitive personal data under the DPDP Act 2023; a single missing queryset
filter would expose one customer's measurements to another.

Two conventions are asserted throughout:

* A foreign object returns **404, not 403**. A 403 confirms the resource
  exists, which is an enumeration oracle.
* Read access to the catalogue is public; everything personal is default-deny.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.enums import ProductStatus
from apps.orders.models import Order, OrderStatus
from apps.tailoring.models import BespokeFitProfile
from apps.users.models import UserRole
from tests.factories import make_product, make_user, make_variant

pytestmark = pytest.mark.django_db

ROLES = [
    UserRole.CUSTOMER,
    UserRole.VENDOR,
    UserRole.TAILOR,
    UserRole.STYLIST,
    UserRole.STAFF,
    UserRole.ADMIN,
]


def client_for(api_client, user):
    from apps.users.serializers import FerashaTokenObtainPairSerializer

    token = FerashaTokenObtainPairSerializer.get_token(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.fixture
def owner(db):
    return make_user(email="owner@example.com", full_name="Ayesha Khan")


@pytest.fixture
def intruder(db):
    return make_user(email="intruder@example.com", full_name="Nosy Person")


@pytest.fixture
def owner_profile(owner):
    return BespokeFitProfile.objects.create(
        user=owner,
        label="My measurements",
        measurements={"bust": 36, "waist": 30, "hip": 38},
        unit_system="inch",
    )


@pytest.fixture
def owner_order(owner):
    return Order.objects.create(
        order_number="FER-AUTHZ-1",
        customer=owner,
        status=OrderStatus.PLACED,
        place_of_supply_state="MH",
    )


# ---------------------------------------------------------------------------
# Fit profiles - the most sensitive resource in the platform
# ---------------------------------------------------------------------------


class TestFitProfileIsolation:
    def test_anonymous_cannot_list(self, api_client):
        assert api_client.get(reverse("tailoring:fit-profile-list")).status_code == 401

    def test_anonymous_cannot_retrieve(self, api_client, owner_profile):
        response = api_client.get(
            reverse("tailoring:fit-profile-detail", args=[owner_profile.id])
        )
        assert response.status_code == 401

    def test_owner_sees_own_profile(self, api_client, owner, owner_profile):
        client = client_for(api_client, owner)
        response = client.get(reverse("tailoring:fit-profile-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    @pytest.mark.parametrize("role", ROLES)
    def test_no_role_can_list_another_customers_profile(
        self, api_client, owner_profile, role
    ):
        """Not even staff may browse the full measurement database unscoped."""
        other = make_user(email=f"{role}@example.com", role=role, is_staff=role == UserRole.STAFF)
        client = client_for(api_client, other)
        response = client.get(reverse("tailoring:fit-profile-list"))
        assert response.status_code == 200
        returned_ids = {r["id"] for r in response.data["results"]}
        assert str(owner_profile.id) not in returned_ids, (
            f"role {role} could list another customer's measurements"
        )

    def test_intruder_gets_404_not_403(self, api_client, intruder, owner_profile):
        """404 rather than 403: a 403 would confirm the profile exists."""
        client = client_for(api_client, intruder)
        response = client.get(
            reverse("tailoring:fit-profile-detail", args=[owner_profile.id])
        )
        assert response.status_code == 404

    def test_intruder_cannot_update(self, api_client, intruder, owner_profile):
        client = client_for(api_client, intruder)
        response = client.patch(
            reverse("tailoring:fit-profile-detail", args=[owner_profile.id]),
            {"measurements": {"bust": 99}},
            format="json",
        )
        assert response.status_code == 404
        owner_profile.refresh_from_db()
        assert owner_profile.measurements["bust"] == 36.0

    def test_intruder_cannot_delete(self, api_client, intruder, owner_profile):
        client = client_for(api_client, intruder)
        response = client.delete(
            reverse("tailoring:fit-profile-detail", args=[owner_profile.id])
        )
        assert response.status_code == 404
        assert BespokeFitProfile.objects.filter(pk=owner_profile.pk).exists()

    def test_cannot_create_profile_for_another_user(self, api_client, intruder, owner):
        """The user is taken from the token, never from the payload."""
        client = client_for(api_client, intruder)
        response = client.post(
            reverse("tailoring:fit-profile-list"),
            {
                "label": "Injected",
                "user": str(owner.id),
                "measurements": {"bust": 36},
                "unit_system": "inch",
            },
            format="json",
        )
        assert response.status_code == 201
        created = BespokeFitProfile.objects.get(label="Injected")
        assert created.user == intruder, "user field in the payload was honoured"

    def test_staff_must_scope_to_a_named_customer(self, api_client, owner, owner_profile):
        staff = make_user(email="ops@ferasha.com", role=UserRole.STAFF, is_staff=True)
        client = client_for(api_client, staff)

        unscoped = client.get(reverse("tailoring:fit-profile-list"))
        assert str(owner_profile.id) not in {r["id"] for r in unscoped.data["results"]}

        scoped = client.get(
            reverse("tailoring:fit-profile-list"), {"user": str(owner.id)}
        )
        assert str(owner_profile.id) in {r["id"] for r in scoped.data["results"]}

    def test_customer_cannot_self_verify_measurements(
        self, api_client, owner, owner_profile
    ):
        """Verification is a tailor's attestation, not a customer's claim."""
        client = client_for(api_client, owner)
        response = client.post(
            reverse("tailoring:fit-profile-verify", args=[owner_profile.id])
        )
        assert response.status_code == 403
        owner_profile.refresh_from_db()
        assert owner_profile.verified_at is None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestOrderIsolation:
    def test_anonymous_cannot_list(self, api_client):
        assert api_client.get(reverse("orders:order-list")).status_code == 401

    def test_owner_sees_own_order(self, api_client, owner, owner_order):
        client = client_for(api_client, owner)
        response = client.get(reverse("orders:order-list"))
        assert response.status_code == 200
        assert response.data["results"][0]["order_number"] == "FER-AUTHZ-1"

    def test_intruder_cannot_list_foreign_order(self, api_client, intruder, owner_order):
        client = client_for(api_client, intruder)
        response = client.get(reverse("orders:order-list"))
        assert response.data["results"] == []

    def test_intruder_gets_404_on_foreign_order(self, api_client, intruder, owner_order):
        client = client_for(api_client, intruder)
        response = client.get(
            reverse("orders:order-detail", args=[owner_order.order_number])
        )
        assert response.status_code == 404

    def test_staff_can_read_any_order(self, api_client, owner_order):
        staff = make_user(email="ops2@ferasha.com", role=UserRole.STAFF, is_staff=True)
        client = client_for(api_client, staff)
        response = client.get(
            reverse("orders:order-detail", args=[owner_order.order_number])
        )
        assert response.status_code == 200

    def test_customer_cannot_transition_own_order(self, api_client, owner, owner_order):
        """A customer must not be able to mark their own order delivered."""
        client = client_for(api_client, owner)
        response = client.post(
            reverse("orders:order-transition", args=[owner_order.order_number]),
            {"status": OrderStatus.PAYMENT_CONFIRMED},
            format="json",
        )
        assert response.status_code == 403
        owner_order.refresh_from_db()
        assert owner_order.status == OrderStatus.PLACED

    def test_vendor_cannot_transition_orders(self, api_client, owner_order):
        vendor = make_user(email="v@example.com", role=UserRole.VENDOR)
        client = client_for(api_client, vendor)
        response = client.post(
            reverse("orders:order-transition", args=[owner_order.order_number]),
            {"status": OrderStatus.PAYMENT_CONFIRMED},
            format="json",
        )
        assert response.status_code in (403, 404)

    def test_staff_can_transition(self, api_client, owner_order):
        staff = make_user(email="ops3@ferasha.com", role=UserRole.STAFF, is_staff=True)
        client = client_for(api_client, staff)
        response = client.post(
            reverse("orders:order-transition", args=[owner_order.order_number]),
            {"status": OrderStatus.PAYMENT_CONFIRMED},
            format="json",
        )
        assert response.status_code == 200
        owner_order.refresh_from_db()
        assert owner_order.status == OrderStatus.PAYMENT_CONFIRMED

    def test_illegal_transition_returns_409(self, api_client, owner_order):
        staff = make_user(email="ops4@ferasha.com", role=UserRole.STAFF, is_staff=True)
        client = client_for(api_client, staff)
        response = client.post(
            reverse("orders:order-transition", args=[owner_order.order_number]),
            {"status": OrderStatus.DELIVERED},
            format="json",
        )
        assert response.status_code == 409
        assert "OrderStatus." not in response.data["detail"]

    def test_order_number_enumeration_is_not_rewarded(self, api_client, intruder):
        """A guessed order number must be indistinguishable from a missing one."""
        client = client_for(api_client, intruder)
        real_missing = client.get(reverse("orders:order-detail", args=["FER-999999"]))
        assert real_missing.status_code == 404


# ---------------------------------------------------------------------------
# Catalogue - public read, restricted write
# ---------------------------------------------------------------------------


class TestCatalogueAccess:
    def test_anonymous_can_browse(self, api_client):
        make_product(slug="public-1")
        response = api_client.get(reverse("catalog:product-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_anonymous_cannot_see_drafts(self, api_client):
        make_product(slug="draft-1", status=ProductStatus.DRAFT)
        response = api_client.get(reverse("catalog:product-list"))
        assert response.data["results"] == []

    def test_anonymous_cannot_create(self, api_client):
        response = api_client.post(
            reverse("catalog:product-list"), {"name": "Sneaky"}, format="json"
        )
        assert response.status_code == 401

    def test_customer_cannot_create(self, api_client, owner):
        client = client_for(api_client, owner)
        response = client.post(
            reverse("catalog:product-list"), {"name": "Sneaky"}, format="json"
        )
        assert response.status_code == 403

    def test_vendor_can_create_own_product(self, api_client):
        from tests.factories import make_category

        vendor = make_user(email="vendor-a@example.com", role=UserRole.VENDOR)
        client = client_for(api_client, vendor)
        response = client.post(
            reverse("catalog:product-list"),
            {
                "name": "Chiffon Suit",
                "slug": "chiffon-suit-a",
                "category": str(make_category().id),
                "garment_type": "suit_set",
                "fabric": "chiffon",
                "work_type": "plain",
                "occasion": "formal",
                "base_price": "8000.00",
                "hsn_code": "6204",
                "is_opaque": True,
                "has_full_lining": True,
                "slit_coverage": "none",
                "sleeve_coverage": "full",
                "neckline_modesty": "high",
                "back_coverage": "full",
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        from apps.catalog.models import Product

        assert Product.objects.get(slug="chiffon-suit-a").vendor == vendor

    def test_vendor_cannot_edit_another_vendors_product(self, api_client):
        vendor_a = make_user(email="vendor-1@example.com", role=UserRole.VENDOR)
        vendor_b = make_user(email="vendor-2@example.com", role=UserRole.VENDOR)
        product = make_product(slug="belongs-to-a", vendor=vendor_a)

        client = client_for(api_client, vendor_b)
        response = client.patch(
            reverse("catalog:product-detail", args=[product.slug]),
            {"base_price": "1.00"},
            format="json",
        )
        assert response.status_code == 403
        product.refresh_from_db()
        assert product.base_price != Decimal("1.00")

    def test_vendor_sees_own_drafts_but_not_others(self, api_client):
        vendor_a = make_user(email="vendor-3@example.com", role=UserRole.VENDOR)
        vendor_b = make_user(email="vendor-4@example.com", role=UserRole.VENDOR)
        make_product(slug="a-draft", vendor=vendor_a, status=ProductStatus.DRAFT)
        make_product(slug="b-draft", vendor=vendor_b, status=ProductStatus.DRAFT)

        client = client_for(api_client, vendor_a)
        slugs = {p["slug"] for p in client.get(reverse("catalog:product-list")).data["results"]}
        assert "a-draft" in slugs
        assert "b-draft" not in slugs

    def test_stock_quantity_is_never_exposed(self, api_client):
        """Exact inventory reveals sales velocity to competitors."""
        product = make_product(slug="stocked")
        make_variant(product=product, stock_quantity=7)
        response = api_client.get(reverse("catalog:product-detail", args=["stocked"]))
        assert response.status_code == 200
        variant = response.data["variants"][0]
        assert "stock_quantity" not in variant
        assert variant["in_stock"] is True


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class TestReviewAccess:
    def test_anonymous_can_read(self, api_client):
        assert api_client.get(reverse("reviews:review-list")).status_code == 200

    def test_anonymous_cannot_write(self, api_client):
        product = make_product()
        response = api_client.post(
            reverse("reviews:review-list"),
            {"product": str(product.id), "rating": 5},
            format="json",
        )
        assert response.status_code == 401

    def test_author_cannot_be_forged(self, api_client, owner, intruder):
        product = make_product()
        client = client_for(api_client, intruder)
        response = client.post(
            reverse("reviews:review-list"),
            {"product": str(product.id), "rating": 5, "author": str(owner.id)},
            format="json",
        )
        assert response.status_code == 201
        from apps.reviews.models import Review

        assert Review.objects.get(product=product).author == intruder

    def test_unverified_purchase_is_not_badged(self, api_client, owner):
        product = make_product()
        client = client_for(api_client, owner)
        response = client.post(
            reverse("reviews:review-list"),
            {"product": str(product.id), "rating": 5, "body": "Lovely"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["is_verified_purchase"] is False

    def test_duplicate_review_rejected(self, api_client, owner):
        product = make_product()
        client = client_for(api_client, owner)
        payload = {"product": str(product.id), "rating": 5}
        assert client.post(reverse("reviews:review-list"), payload, format="json").status_code == 201
        second = client.post(reverse("reviews:review-list"), payload, format="json")
        assert second.status_code == 400

    def test_pending_review_hidden_from_others(self, api_client, owner, intruder):
        product = make_product()
        client_for(api_client, owner).post(
            reverse("reviews:review-list"),
            {"product": str(product.id), "rating": 5, "body": "Pending"},
            format="json",
        )
        other = client_for(api_client, intruder)
        assert other.get(reverse("reviews:review-list")).data["results"] == []

    def test_only_first_name_published(self, api_client, owner):
        product = make_product()
        client = client_for(api_client, owner)
        response = client.post(
            reverse("reviews:review-list"),
            {"product": str(product.id), "rating": 4},
            format="json",
        )
        assert response.data["author_name"] == "Ayesha"
        assert "Khan" not in response.data["author_name"]


class TestOrderTimelineRedaction:
    """The order timeline is shared between customers and back office.

    Staff write ``reason`` for internal consumption ("fabric shortage", "fraud
    review") and ``actor`` names an employee. Neither may reach the customer,
    even on their *own* order - ownership grants access to the order, not to
    internal deliberation about it.
    """

    @pytest.fixture
    def order_with_event(self, owner):
        from apps.orders.models import OrderEvent

        order = Order.objects.create(
            order_number="FER-AUTHZ-EVT",
            customer=owner,
            status=OrderStatus.IN_ATELIER,
            place_of_supply_state="MH",
        )
        staff = make_user(
            email="atelier.lead@ferasha.com", role=UserRole.STAFF, is_staff=True,
            full_name="Farah Siddiqui",
        )
        OrderEvent.objects.create(
            order=order,
            from_status=OrderStatus.PLACED,
            to_status=OrderStatus.IN_ATELIER,
            actor=staff,
            reason="Fabric shortage - reorder raised with Karachi mill",
        )
        return order

    def test_customer_cannot_see_internal_reason_or_actor(
        self, api_client, owner, order_with_event
    ):
        client = client_for(api_client, owner)
        response = client.get(
            reverse("orders:order-detail", args=[order_with_event.order_number])
        )
        assert response.status_code == 200

        events = response.data["events"]
        assert len(events) == 1
        event = events[0]

        assert event["from_status"] == OrderStatus.PLACED
        assert event["to_status"] == OrderStatus.IN_ATELIER
        assert "reason" not in event, "internal note leaked to the customer"
        assert "actor_name" not in event, "staff identity leaked to the customer"

        # Belt and braces: the strings must not appear anywhere in the payload.
        body = str(response.data)
        assert "Fabric shortage" not in body
        assert "Farah Siddiqui" not in body

    def test_back_office_still_sees_the_full_audit_trail(self, api_client, order_with_event):
        staff = make_user(email="ops.audit@ferasha.com", role=UserRole.STAFF, is_staff=True)
        client = client_for(api_client, staff)
        response = client.get(
            reverse("orders:order-detail", args=[order_with_event.order_number])
        )
        assert response.status_code == 200

        event = response.data["events"][0]
        assert event["reason"] == "Fabric shortage - reorder raised with Karachi mill"
        assert event["actor_name"] == "Farah Siddiqui"

    def test_customer_does_not_receive_next_statuses(self, api_client, owner, order_with_event):
        """Available transitions describe internal workflow, not customer options."""
        client = client_for(api_client, owner)
        response = client.get(
            reverse("orders:order-detail", args=[order_with_event.order_number])
        )
        assert response.data["next_statuses"] == []
