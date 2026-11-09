"""The owner dashboard's numbers.

Computed in a small fixed number of queries, whatever the size of the
catalogue or the order book. Days are the atelier's days (TIME_ZONE,
Asia/Kolkata): an order placed at 23:30 in Mumbai belongs to that date, not to
the UTC one.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.catalog.enums import ProductStatus, SizeStandard
from apps.catalog.models import ProductVariant
from apps.media_assets.models import MediaAsset, ModerationStatus
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import OrderListSerializer
from apps.orders.state_machine import OPEN_STATUSES, REVENUE_STATUSES
from apps.reviews.models import Review, ReviewStatus

#: A size at or below this many pieces is worth restocking.
LOW_STOCK_AT = 2
SERIES_DAYS = 30
RECENT_ORDERS = 6
LOW_STOCK_ROWS = 8


def _money(value: Decimal | None) -> str:
    return str((value or Decimal("0")).quantize(Decimal("0.01")))


def dashboard_summary(request) -> dict:
    zone = timezone.get_current_timezone()
    today = timezone.localtime(timezone.now(), zone).date()

    def start_of(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=zone)

    paid = Order.objects.filter(status__in=REVENUE_STATUSES, placed_at__isnull=False).order_by()

    def totals(first: date, last: date) -> dict:
        return paid.filter(
            placed_at__gte=start_of(first), placed_at__lt=start_of(last + timedelta(days=1))
        ).aggregate(revenue=Sum("grand_total"), orders=Count("id"))

    # Month to date against the same days of last month, so the 5th is not
    # compared with a whole month. A short month is clamped: 31 Mar vs 28 Feb.
    month_start = today.replace(day=1)
    previous_last = month_start - timedelta(days=1)
    previous_start = previous_last.replace(day=1)
    current = totals(month_start, today)
    previous = totals(previous_start, previous_start.replace(day=min(today.day, previous_last.day)))

    first_day = today - timedelta(days=SERIES_DAYS - 1)
    by_day = {
        row["day"]: row
        for row in paid.filter(placed_at__gte=start_of(first_day))
        .annotate(day=TruncDate("placed_at", tzinfo=zone))
        .values("day")
        .annotate(revenue=Sum("grand_total"), orders=Count("id"))
    }
    series = []
    for offset in range(SERIES_DAYS):
        day = first_day + timedelta(days=offset)
        row = by_day.get(day, {})
        series.append({"date": day.isoformat(), "revenue": _money(row.get("revenue")), "orders": row.get("orders", 0)})

    # Every open stage, empty ones included: an empty stage is good news.
    open_counts = dict(
        Order.objects.filter(status__in=OPEN_STATUSES).order_by().values_list("status").annotate(n=Count("id"))
    )
    pipeline = [
        {"status": status, "label": str(OrderStatus(status).label), "count": open_counts.get(status, 0)}
        for status in OPEN_STATUSES
    ]

    low_stock = (
        ProductVariant.objects.filter(
            is_active=True, product__status=ProductStatus.ACTIVE, stock_quantity__lte=LOW_STOCK_AT
        )
        # Made to measure is stitched per order and never stocked.
        .exclude(size=SizeStandard.CUSTOM)
        .select_related("product")
        .order_by("stock_quantity", "product__name", "size")[:LOW_STOCK_ROWS]
    )
    recent = (
        Order.objects.filter(placed_at__isnull=False)
        .select_related("customer")
        .prefetch_related("lines")
        .annotate(line_count=Count("lines", distinct=True))
        .order_by("-placed_at", "-pk")[:RECENT_ORDERS]
    )

    return {
        "currency": "INR",
        "revenue": {"month_to_date": _money(current["revenue"]), "previous_period": _money(previous["revenue"])},
        "orders": {"month_to_date": current["orders"], "previous_period": previous["orders"]},
        "average_order_value": _money(current["revenue"] / current["orders"]) if current["orders"] else None,
        "series": series,
        "pipeline": pipeline,
        "moderation": {
            "reviews_pending": Review.objects.filter(status=ReviewStatus.PENDING).count(),
            "photos_needing_review": MediaAsset.objects.filter(
                moderation_status=ModerationStatus.NEEDS_REVIEW
            ).count(),
        },
        "low_stock": [
            {
                "sku": variant.sku,
                "product_name": variant.product.name,
                "product_slug": variant.product.slug,
                "size": variant.size,
                "colour": variant.colour,
                "stock_quantity": variant.stock_quantity,
            }
            for variant in low_stock
        ],
        "recent_orders": OrderListSerializer(recent, many=True, context={"request": request}).data,
    }
