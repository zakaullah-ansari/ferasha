"""The owner dashboard's summary: honest numbers, for the back office only.

Revenue counts paid orders only (an unpaid order is not money), month to date
against the same days of the previous month, in the atelier's own time zone.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from apps.media_assets.models import ModerationStatus
from apps.orders.models import Order, OrderStatus
from apps.reviews.models import Review, ReviewStatus
from tests.conftest import _client_for
from tests.factories import make_asset, make_product, make_user, make_variant

pytestmark = pytest.mark.django_db

SUMMARY = reverse("backoffice:summary")
IST = ZoneInfo("Asia/Kolkata")
#: 20 November, so "month to date" is 1-20 Nov and the comparison 1-20 Oct.
NOW = datetime(2026, 11, 20, 18, 0, tzinfo=IST)
S = OrderStatus


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr("apps.backoffice.services.timezone.now", lambda: NOW)


def order(status: str, total: str, placed: datetime | None, **kw) -> Order:
    return Order.objects.create(
        order_number=f"FER-{Order.objects.count() + 1:06d}",
        status=status,
        grand_total=Decimal(total),
        placed_at=placed,
        **{"guest_email": "guest@example.com", **kw},
    )


@pytest.fixture
def staff_client(staff_user):
    return _client_for(staff_user)


class TestAccess:
    def test_anonymous_is_refused(self, api_client):
        assert api_client.get(SUMMARY).status_code == 401

    def test_a_customer_is_refused(self, auth_client):
        assert auth_client.get(SUMMARY).status_code == 403

    def test_the_back_office_is_served(self, staff_client):
        assert staff_client.get(SUMMARY).status_code == 200


class TestRevenue:
    def test_only_paid_orders_count(self, staff_client, frozen):
        day = datetime(2026, 11, 5, 12, tzinfo=IST)
        order(S.PAYMENT_CONFIRMED, "12000.00", day)
        order(S.SHIPPED, "8000.00", day)
        order(S.PLACED, "50000.00", day)  # awaiting payment
        order(S.CANCELLED, "9000.00", day)
        order(S.REFUNDED, "7000.00", day)

        data = staff_client.get(SUMMARY).json()

        assert data["revenue"] == {"month_to_date": "20000.00", "previous_period": "0.00"}
        assert data["orders"] == {"month_to_date": 2, "previous_period": 0}
        assert data["average_order_value"] == "10000.00"

    def test_compares_with_the_same_days_last_month(self, staff_client, frozen):
        order(S.DELIVERED, "4000.00", datetime(2026, 10, 20, 17, tzinfo=IST))  # inside 1-20 Oct
        order(S.DELIVERED, "9999.00", datetime(2026, 10, 25, 12, tzinfo=IST))  # after the 20th

        assert staff_client.get(SUMMARY).json()["revenue"]["previous_period"] == "4000.00"

    def test_days_are_the_atelier_s_days(self, staff_client, frozen):
        # 23:30 IST on 31 Oct is 18:00 UTC on 31 Oct: October, not November.
        order(S.STITCHING, "5000.00", datetime(2026, 10, 31, 23, 30, tzinfo=IST))

        data = staff_client.get(SUMMARY).json()

        assert data["revenue"]["month_to_date"] == "0.00"
        assert {"date": "2026-10-31", "revenue": "5000.00", "orders": 1} in data["series"]

    def test_the_series_has_every_day_even_quiet_ones(self, staff_client, frozen):
        order(S.PACKED, "3000.00", datetime(2026, 11, 19, 10, tzinfo=IST))
        order(S.PACKED, "2000.00", datetime(2026, 11, 19, 15, tzinfo=IST))

        series = staff_client.get(SUMMARY).json()["series"]

        assert len(series) == 30
        assert series[0]["date"] == "2026-10-22"
        assert series[-1]["date"] == "2026-11-20"
        assert series[-2] == {"date": "2026-11-19", "revenue": "5000.00", "orders": 2}
        assert series[-1] == {"date": "2026-11-20", "revenue": "0.00", "orders": 0}

    def test_no_sales_means_no_average(self, staff_client, frozen):
        assert staff_client.get(SUMMARY).json()["average_order_value"] is None


class TestWhatNeedsAttention:
    def test_open_orders_by_stage_in_pipeline_order(self, staff_client, frozen):
        day = datetime(2026, 11, 18, tzinfo=IST)
        for status in (S.PAYMENT_CONFIRMED, S.PAYMENT_CONFIRMED, S.QUALITY_CHECK, S.DELIVERED):
            order(status, "1000.00", day)

        pipeline = staff_client.get(SUMMARY).json()["pipeline"]

        assert [stage["status"] for stage in pipeline][:3] == ["placed", "payment_confirmed", "measurement_review"]
        counts = {stage["status"]: stage["count"] for stage in pipeline}
        assert counts["payment_confirmed"] == 2
        assert counts["quality_check"] == 1
        assert "delivered" not in counts  # finished, nothing to do
        assert pipeline[1]["label"] == "Payment confirmed"

    def test_moderation_queues(self, staff_client):
        product = make_product()
        Review.objects.create(product=product, author=make_user(), rating=5)
        Review.objects.create(product=product, author=make_user(), rating=4, status=ReviewStatus.PUBLISHED)
        make_asset(moderation_status=ModerationStatus.NEEDS_REVIEW)
        make_asset()

        assert staff_client.get(SUMMARY).json()["moderation"] == {"reviews_pending": 1, "photos_needing_review": 1}

    def test_low_stock_lists_the_scarcest_sellable_sizes(self, staff_client):
        product = make_product(name="Velvet Gharara")
        make_variant(product=product, sku="VG-S", size="S", stock_quantity=0)
        make_variant(product=product, sku="VG-M", size="M", stock_quantity=2)
        make_variant(product=product, sku="VG-L", size="L", stock_quantity=9)
        make_variant(product=product, sku="VG-XL", size="XL", stock_quantity=1, is_active=False)

        low = staff_client.get(SUMMARY).json()["low_stock"]

        assert [(row["sku"], row["stock_quantity"]) for row in low] == [("VG-S", 0), ("VG-M", 2)]
        assert low[0]["product_name"] == "Velvet Gharara"

    def test_made_to_measure_is_never_low_on_stock(self, staff_client):
        # Stitched to order: a CUSTOM variant holds no stock by design.
        make_variant(sku="BESPOKE", size="CUSTOM", stock_quantity=0)

        assert staff_client.get(SUMMARY).json()["low_stock"] == []

    def test_recent_orders_newest_first(self, staff_client, frozen):
        first = order(S.PLACED, "1000.00", datetime(2026, 11, 1, tzinfo=IST))
        second = order(S.PLACED, "2000.00", datetime(2026, 11, 2, tzinfo=IST))

        recent = staff_client.get(SUMMARY).json()["recent_orders"]

        assert [row["order_number"] for row in recent] == [second.order_number, first.order_number]
        assert recent[0]["customer_name"] == "guest@example.com"  # the back office sees who


ORDERS = reverse("orders:order-list")


class TestOrderListForTheBackOffice:
    def test_filters_by_one_or_more_stages(self, staff_client):
        order(S.PAYMENT_CONFIRMED, "1000.00", NOW)
        order(S.PACKED, "1000.00", NOW)
        order(S.SHIPPED, "1000.00", NOW)

        data = staff_client.get(ORDERS, {"status": ["payment_confirmed", "packed"]}).json()

        assert sorted(row["status"] for row in data["results"]) == ["packed", "payment_confirmed"]

    def test_searches_by_order_number_and_customer(self, staff_client):
        ayesha = make_user(full_name="Ayesha Khan", email="ayesha@example.com")
        mine = order(S.PLACED, "1000.00", NOW, customer=ayesha, guest_email="")
        order(S.PLACED, "1000.00", NOW)

        by_name = staff_client.get(ORDERS, {"search": "ayesha"}).json()["results"]
        by_number = staff_client.get(ORDERS, {"search": mine.order_number}).json()["results"]

        assert [row["order_number"] for row in by_name] == [mine.order_number]
        assert [row["order_number"] for row in by_number] == [mine.order_number]

    def test_rows_name_the_customer_or_the_guest(self, staff_client):
        ayesha = make_user(full_name="Ayesha Khan")
        order(S.PLACED, "1000.00", NOW, customer=ayesha, guest_email="")
        order(S.PLACED, "1000.00", NOW, shipping_address={"recipient_name": "Sana Mir"})
        order(S.PLACED, "1000.00", NOW, guest_email="noname@example.com")

        names = {row["customer_name"] for row in staff_client.get(ORDERS).json()["results"]}

        assert names == {"Ayesha Khan", "Sana Mir", "noname@example.com"}

    def test_a_customer_cannot_search_their_way_into_other_orders(self, auth_client, staff_user):
        order(S.PLACED, "1000.00", NOW, customer=staff_user, guest_email="")

        assert auth_client.get(ORDERS, {"search": "FER"}).json()["count"] == 0


ME = reverse("users:current-user")


class TestTheSessionSaysWhoMaySeeTheDashboard:
    def test_back_office_and_customer(self, staff_client, auth_client):
        assert staff_client.get(ME).json()["is_back_office"] is True
        assert auth_client.get(ME).json()["is_back_office"] is False

    def test_a_customer_cannot_promote_themselves(self, auth_client, customer):
        auth_client.patch(ME, {"is_back_office": True, "role": "admin"}, format="json")

        customer.refresh_from_db()
        assert customer.is_back_office is False


class TestOrderDetailForTheBackOffice:
    def test_says_who_to_contact(self, staff_client):
        ayesha = make_user(full_name="Ayesha Khan", email="ayesha@example.com")
        mine = order(S.PAYMENT_CONFIRMED, "1000.00", NOW, customer=ayesha, guest_email="")

        data = staff_client.get(reverse("orders:order-detail", args=[mine.order_number])).json()

        assert (data["customer_name"], data["contact_email"]) == ("Ayesha Khan", "ayesha@example.com")
        assert "in_atelier" in data["next_statuses"]


class TestTheAtelierSeesTheWorkNotTheCustomer:
    """Tailors read orders in the atelier; who the customer is stays with the back office."""

    @pytest.fixture
    def tailor_client(self):
        return _client_for(make_user(role="tailor"))

    @pytest.fixture
    def stitching(self):
        ayesha = make_user(full_name="Ayesha Khan", email="ayesha@example.com")
        return order(S.STITCHING, "1000.00", NOW, customer=ayesha, guest_email="")

    def test_no_name_or_email_in_the_list_or_after_moving_an_order(self, tailor_client, stitching):
        row = tailor_client.get(ORDERS).json()["results"][0]
        moved = tailor_client.post(
            reverse("orders:order-transition", args=[stitching.order_number]),
            {"status": "quality_check"},
            format="json",
        )

        assert row["customer_name"] == ""
        assert moved.status_code == 200
        assert (moved.json()["customer_name"], moved.json()["contact_email"]) == ("", "")

    def test_cannot_search_by_customer(self, tailor_client, stitching):
        assert tailor_client.get(ORDERS, {"search": "ayesha@example.com"}).json()["count"] == 0
        assert tailor_client.get(ORDERS, {"search": stitching.order_number}).json()["count"] == 1
