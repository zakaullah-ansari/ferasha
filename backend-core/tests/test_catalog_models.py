"""Catalogue model, constraint and stock-concurrency tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.enums import ProductStatus, SizeStandard, SleeveCoverage, SlitCoverage
from apps.catalog.models import Category, Product, ProductVariant
from apps.catalog.modesty import ModestyBadge
from apps.catalog.services import InsufficientStock, release_stock, reserve_stock
from tests.factories import make_category, make_product, make_variant

pytestmark = pytest.mark.django_db


class TestCategoryTree:
    def test_root_path_is_slug(self):
        root = make_category(name="Bridal", slug="bridal")
        assert root.path == "bridal"
        assert root.depth == 0

    def test_child_path_is_materialised(self):
        root = make_category(name="Bridal", slug="bridal")
        child = Category.objects.create(name="Lehenga", slug="lehenga", parent=root)
        assert child.path == "bridal/lehenga"
        assert child.depth == 1

    def test_grandchild_path(self):
        root = make_category(slug="bridal")
        child = Category.objects.create(name="Lehenga", slug="lehenga", parent=root)
        grand = Category.objects.create(name="Velvet", slug="velvet", parent=child)
        assert grand.path == "bridal/lehenga/velvet"
        assert grand.depth == 2

    def test_subtree_read_is_a_single_query(self, django_assert_num_queries):
        """Materialised path: one indexed prefix scan, not one query per level."""
        root = make_category(slug="bridal")
        child = Category.objects.create(name="Lehenga", slug="lehenga", parent=root)
        Category.objects.create(name="Velvet", slug="velvet", parent=child)
        make_category(slug="casual")

        with django_assert_num_queries(1):
            assert root.descendants().count() == 2
        with django_assert_num_queries(1):
            assert root.self_and_descendants().count() == 3

    def test_unrelated_tree_excluded_from_descendants(self):
        root = make_category(slug="bridal")
        Category.objects.create(name="Lehenga", slug="lehenga", parent=root)
        make_category(slug="bridalwear-outlet")  # shares a prefix, not a parent
        assert root.descendants().count() == 1

    def test_parent_is_protected_from_deletion(self):
        root = make_category(slug="bridal")
        Category.objects.create(name="Lehenga", slug="lehenga", parent=root)
        with pytest.raises(Exception):
            root.delete()


class TestProductConstraints:
    """Constraints must be enforced by PostgreSQL, not only by Python."""

    def test_negative_price_rejected_by_database(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_product(base_price=Decimal("-1.00"))

    def test_compare_at_price_must_exceed_base(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_product(
                    base_price=Decimal("5000.00"), compare_at_price=Decimal("4000.00")
                )

    def test_compare_at_price_above_base_accepted(self):
        product = make_product(
            base_price=Decimal("5000.00"), compare_at_price=Decimal("7000.00")
        )
        assert product.compare_at_price > product.base_price

    def test_bespoke_requires_lead_time(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_product(supports_bespoke=True, stitching_days=0)

    def test_bespoke_with_lead_time_accepted(self):
        product = make_product(supports_bespoke=True, stitching_days=21)
        assert product.stitching_days == 21

    def test_sheer_overlay_cannot_be_opaque(self):
        """Contradictory modesty claims are rejected at the database."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_product(is_sheer_overlay_only=True, is_opaque=True)

    def test_invalid_slit_coverage_rejected(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Product.objects.filter(pk=make_product().pk).update(
                    slit_coverage="scandalous"
                )

    def test_invalid_status_rejected(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Product.objects.filter(pk=make_product().pk).update(status="vibing")

    def test_negative_bespoke_surcharge_rejected(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_product(bespoke_surcharge=Decimal("-100.00"))


class TestProductModesty:
    def test_modesty_derives_from_columns(self):
        product = make_product()
        assert ModestyBadge.FULL_COVERAGE in product.modesty.badges

    def test_queryset_matches_derivation_function(self):
        """The ORM filter and the pure function must never disagree.

        If they drift, a customer filtering for 'fully covered' sees garments
        whose badge says otherwise.
        """
        make_product(slug="covered-1")
        make_product(slug="sleeveless-1", sleeve_coverage=SleeveCoverage.SLEEVELESS)
        make_product(slug="slit-1", slit_coverage=SlitCoverage.THIGH)
        make_product(slug="sheer-1", is_opaque=False, is_sheer_overlay_only=True)
        make_product(slug="slip-1", requires_slip=True)

        by_query = set(Product.objects.fully_covered().values_list("slug", flat=True))
        by_function = {
            p.slug
            for p in Product.objects.all()
            if ModestyBadge.FULL_COVERAGE in p.modesty.badges
        }
        assert by_query == by_function


class TestVariantConstraints:
    def test_negative_stock_rejected_by_database(self):
        variant = make_variant()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.filter(pk=variant.pk).update(stock_quantity=-1)

    def test_duplicate_size_colour_rejected(self):
        product = make_product()
        make_variant(product=product, size=SizeStandard.M, colour="Ivory")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_variant(product=product, size=SizeStandard.M, colour="Ivory")

    def test_same_size_different_colour_allowed(self):
        product = make_product()
        make_variant(product=product, size=SizeStandard.M, colour="Ivory")
        second = make_variant(product=product, size=SizeStandard.M, colour="Gold")
        assert second.pk

    def test_price_includes_delta(self):
        product = make_product(base_price=Decimal("10000.00"))
        variant = make_variant(product=product, price_delta=Decimal("1500.00"))
        assert variant.price == Decimal("11500.00")

    def test_low_stock_flag(self):
        variant = make_variant(stock_quantity=2, low_stock_threshold=2)
        assert variant.is_low_stock is True
        variant.stock_quantity = 0
        assert variant.is_low_stock is False


class TestStockReservation:
    """Overselling the last bridal lehenga is unacceptable."""

    def test_reserve_decrements(self):
        variant = make_variant(stock_quantity=5)
        reserve_stock(variant.pk, 2)
        variant.refresh_from_db()
        assert variant.stock_quantity == 3

    def test_reserve_exact_remaining_succeeds(self):
        variant = make_variant(stock_quantity=3)
        reserve_stock(variant.pk, 3)
        variant.refresh_from_db()
        assert variant.stock_quantity == 0

    def test_over_reservation_refused(self):
        variant = make_variant(stock_quantity=2)
        with pytest.raises(InsufficientStock) as exc:
            reserve_stock(variant.pk, 3)
        assert exc.value.available == 2
        variant.refresh_from_db()
        assert variant.stock_quantity == 2, "stock must be untouched on failure"

    def test_reserve_from_zero_refused(self):
        variant = make_variant(stock_quantity=0)
        with pytest.raises(InsufficientStock):
            reserve_stock(variant.pk, 1)

    def test_sequential_reservations_cannot_oversell(self):
        """Simulates the race: both callers believe 1 unit is available."""
        variant = make_variant(stock_quantity=1)
        reserve_stock(variant.pk, 1)
        with pytest.raises(InsufficientStock):
            reserve_stock(variant.pk, 1)
        variant.refresh_from_db()
        assert variant.stock_quantity == 0

    def test_release_restores(self):
        variant = make_variant(stock_quantity=5)
        reserve_stock(variant.pk, 3)
        release_stock(variant.pk, 3)
        variant.refresh_from_db()
        assert variant.stock_quantity == 5

    def test_zero_quantity_rejected(self):
        variant = make_variant()
        with pytest.raises(ValueError):
            reserve_stock(variant.pk, 0)


class TestProductQuerySet:
    def test_active_excludes_drafts(self):
        make_product(slug="live-1", status=ProductStatus.ACTIVE)
        make_product(slug="draft-1", status=ProductStatus.DRAFT)
        assert list(Product.objects.active().values_list("slug", flat=True)) == ["live-1"]

    def test_purchasable_requires_stock(self):
        in_stock = make_product(slug="has-stock")
        make_variant(product=in_stock, stock_quantity=4)
        out = make_product(slug="no-stock")
        make_variant(product=out, stock_quantity=0)

        slugs = set(Product.objects.purchasable().values_list("slug", flat=True))
        assert slugs == {"has-stock"}
