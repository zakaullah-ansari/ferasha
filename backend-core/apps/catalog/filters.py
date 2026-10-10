"""Faceted filtering over the catalogue.

Filtering runs against the typed modesty columns from Phase 1 - the reason they
are not stored as JSON. Ordering is allow-listed rather than interpolated from
the query string.
"""

from __future__ import annotations

import django_filters as filters
from django.db.models import Q

from .enums import (
    BackCoverage,
    Fabric,
    GarmentType,
    NecklineModesty,
    Occasion,
    SleeveCoverage,
    SlitCoverage,
    WorkType,
)
from .models import Category, Product


class ProductFilter(filters.FilterSet):
    """Storefront facets.

    The modesty filters are the differentiating capability of this catalogue,
    so they are first-class query parameters rather than a generic attribute
    lookup.
    """

    category = filters.CharFilter(method="filter_category")
    fabric = filters.MultipleChoiceFilter(choices=Fabric.choices)
    work_type = filters.MultipleChoiceFilter(choices=WorkType.choices)
    occasion = filters.MultipleChoiceFilter(choices=Occasion.choices)
    garment_type = filters.MultipleChoiceFilter(choices=GarmentType.choices)

    price_min = filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="base_price", lookup_expr="lte")

    # --- Modesty facets -----------------------------------------------------
    is_opaque = filters.BooleanFilter()
    has_full_lining = filters.BooleanFilter()
    slit_coverage = filters.MultipleChoiceFilter(choices=SlitCoverage.choices)
    sleeve_coverage = filters.MultipleChoiceFilter(choices=SleeveCoverage.choices)
    neckline_modesty = filters.MultipleChoiceFilter(choices=NecklineModesty.choices)
    back_coverage = filters.MultipleChoiceFilter(choices=BackCoverage.choices)

    #: Single switch for the strongest modesty claim. Delegates to the same
    #: queryset method the badge derivation is tested against, so the filter
    #: and the badge can never disagree.
    fully_covered = filters.BooleanFilter(method="filter_fully_covered")
    full_sleeves = filters.BooleanFilter(method="filter_full_sleeves")
    no_slit = filters.BooleanFilter(method="filter_no_slit")

    supports_bespoke = filters.BooleanFilter()
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    search = filters.CharFilter(method="filter_search")

    ordering = filters.OrderingFilter(
        fields=(
            ("base_price", "price"),
            ("created_at", "created"),
            ("name", "name"),
        ),
    )

    class Meta:
        model = Product
        fields: list[str] = []

    def filter_category(self, queryset, name, value):
        """Include descendants, so 'bridal' returns lehengas and shararas."""
        try:
            category = Category.objects.get(slug=value)
        except Category.DoesNotExist:
            return queryset.none()
        return queryset.filter(category__in=category.self_and_descendants())

    def filter_fully_covered(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.fully_covered() if value else queryset

    def filter_full_sleeves(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            sleeve_coverage__in=[SleeveCoverage.FULL, SleeveCoverage.EXTRA_LONG]
        )

    def filter_no_slit(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(slit_coverage=SlitCoverage.NONE)

    def filter_in_stock(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(variants__stock_quantity__gt=0).distinct()

    def filter_search(self, queryset, name, value):
        """Domain-aware search.

        Customers search 'gharara', 'farshi palazzo', 'chikankari' and misspell
        all of them. Full Postgres FTS with a synonym dictionary arrives in
        Phase 6; this is an honest icontains fallback that works on any backend.
        """
        term = value.strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(name__icontains=term)
            | Q(description__icontains=term)
            | Q(fabric__icontains=term)
            | Q(work_type__icontains=term)
            | Q(category__name__icontains=term)
        ).distinct()
