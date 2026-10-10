"""Query-count budgets for the read-heavy endpoints.

These are regression guards, not micro-benchmarks. The failure mode they exist
to catch is an N+1 introduced by adding a field to a serializer: the response
stays correct, the tests stay green, and the catalogue quietly issues one query
per product per image. The budget makes that a build failure.

Each budget is asserted to be **independent of the number of rows** — the test
runs the same endpoint against a small and a large fixture and requires an
identical count. That is a stronger and less brittle property than pinning an
absolute number, which drifts every time an unrelated middleware changes.
"""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalog.enums import ProductStatus, SizeStandard
from tests.factories import make_category, make_product, make_variant

pytestmark = pytest.mark.django_db


def _populate(count: int, slug_prefix: str) -> None:
    """Create ``count`` published products, each with variants."""
    category = make_category(slug=f"{slug_prefix}-cat")
    for index in range(count):
        product = make_product(
            slug=f"{slug_prefix}-{index}",
            category=category,
            status=ProductStatus.ACTIVE,
        )
        for size in (SizeStandard.S, SizeStandard.M, SizeStandard.L):
            make_variant(
                product=product, size=size, sku=f"{slug_prefix}-{index}-{size.value}"
            )


class TestCatalogueQueryBudget:
    def test_product_list_query_count_is_constant(self, client):
        """Ten times the rows must not mean ten times the queries."""
        _populate(2, "small")
        url = reverse("catalog:product-list")

        with CaptureQueriesContext(connection) as small:
            assert client.get(url).status_code == 200
        baseline = len(small.captured_queries)

        _populate(20, "large")
        with CaptureQueriesContext(connection) as large:
            assert client.get(url).status_code == 200

        assert len(large.captured_queries) == baseline, (
            f"query count grew from {baseline} to {len(large.captured_queries)} "
            "when the row count grew - this is an N+1"
        )

    def test_product_list_budget_is_small(self, client):
        """Guard the absolute ceiling as well, to catch a bloated baseline."""
        _populate(15, "ceiling")
        with CaptureQueriesContext(connection) as captured:
            response = client.get(reverse("catalog:product-list"))
        assert response.status_code == 200

        # count + page + prefetch(images, assets, variants) + a little slack.
        assert len(captured.captured_queries) <= 8, (
            f"catalogue list issued {len(captured.captured_queries)} queries:\n"
            + "\n".join(q["sql"][:160] for q in captured.captured_queries)
        )

    def test_product_detail_query_count_is_constant(self, client):
        _populate(1, "detail")
        url = reverse("catalog:product-detail", args=["detail-0"])

        with CaptureQueriesContext(connection) as before:
            assert client.get(url).status_code == 200
        baseline = len(before.captured_queries)

        # More variants and more sibling products must not change the count.
        product = make_product(slug="detail-extra", status=ProductStatus.ACTIVE)
        for size in (SizeStandard.XS, SizeStandard.XL):
            make_variant(product=product, size=size, sku=f"detail-extra-{size.value}")

        with CaptureQueriesContext(connection) as after:
            assert client.get(url).status_code == 200

        assert len(after.captured_queries) == baseline

    def test_category_tree_is_one_query(self, client):
        """The tree is assembled in Python; recursion into the DB is a bug."""
        from apps.catalog.models import Category

        root = make_category(slug="bridal-budget")
        for name in ("lehenga", "sharara", "gharara"):
            child = Category.objects.create(name=name.title(), slug=f"{name}-b", parent=root)
            Category.objects.create(name=f"{name} silk", slug=f"{name}-silk-b", parent=child)

        with CaptureQueriesContext(connection) as captured:
            response = client.get(reverse("catalog:category-tree"))

        assert response.status_code == 200
        selects = [q for q in captured.captured_queries if q["sql"].lstrip().upper().startswith("SELECT")]
        assert len(selects) == 1, (
            "category tree must be assembled from a single flat query, got "
            f"{len(selects)}"
        )
