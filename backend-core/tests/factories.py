"""Test factories for the Ferasha domain."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.catalog.enums import (
    BackCoverage,
    Fabric,
    GarmentType,
    NecklineModesty,
    Occasion,
    ProductStatus,
    SizeStandard,
    SleeveCoverage,
    SlitCoverage,
    WorkType,
)
from apps.catalog.models import Category, Product, ProductVariant
from apps.users.models import UserRole

User = get_user_model()

_counter = {"n": 0}


def _next() -> int:
    _counter["n"] += 1
    return _counter["n"]


def make_user(**kw):
    n = _next()
    defaults = dict(
        email=f"user{n}@example.com",
        password="Correct-Horse-9182",
        full_name=f"Test User {n}",
    )
    defaults.update(kw)
    password = defaults.pop("password")
    return User.objects.create_user(password=password, **defaults)


def make_vendor(**kw):
    kw.setdefault("role", UserRole.VENDOR)
    return make_user(**kw)


def make_category(**kw):
    n = _next()
    defaults = dict(name=f"Category {n}", slug=f"category-{n}")
    defaults.update(kw)
    return Category.objects.create(**defaults)


def make_product(**kw):
    n = _next()
    defaults = dict(
        name=f"Product {n}",
        slug=f"product-{n}",
        garment_type=GarmentType.SUIT_SET,
        fabric=Fabric.CHIFFON,
        work_type=WorkType.ZARDOZI,
        occasion=Occasion.BRIDAL,
        base_price=Decimal("12000.00"),
        hsn_code="6204",
        status=ProductStatus.ACTIVE,
        is_opaque=True,
        has_full_lining=True,
        slit_coverage=SlitCoverage.NONE,
        sleeve_coverage=SleeveCoverage.FULL,
        neckline_modesty=NecklineModesty.HIGH,
        back_coverage=BackCoverage.FULL,
    )
    defaults.update(kw)
    if "vendor" not in defaults:
        defaults["vendor"] = make_vendor()
    if "category" not in defaults:
        defaults["category"] = make_category()
    return Product.objects.create(**defaults)


def make_variant(product=None, **kw):
    n = _next()
    product = product or make_product()
    defaults = dict(
        product=product,
        sku=f"SKU-{n:05d}",
        size=SizeStandard.M,
        colour="Ivory",
        stock_quantity=10,
    )
    defaults.update(kw)
    return ProductVariant.objects.create(**defaults)
