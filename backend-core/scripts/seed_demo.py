"""Seed the demo database with a representative Ferasha catalogue.

Run against ``config.settings_demo`` only. This exists so the API preview
shows realistic modesty attributes, GST behaviour across the Rs 2,500 slab
boundary, and a populated category tree - an empty catalogue tells you
nothing about whether the serializers are correct.

Idempotent: safe to re-run.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_demo")

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from apps.catalog.enums import (  # noqa: E402
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
from apps.catalog.models import Category, Product, ProductVariant  # noqa: E402
from apps.users.models import UserRole  # noqa: E402

User = get_user_model()


def category(name: str, slug: str, parent=None, order: int = 0) -> Category:
    obj, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "parent": parent, "display_order": order, "is_active": True},
    )
    return obj


def main() -> None:
    # ---------------------------------------------------------------- users
    admin, created = User.objects.get_or_create(
        email="owner@ferasha.com",
        defaults={
            "full_name": "Ferasha Atelier",
            "role": UserRole.ADMIN,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        admin.set_password("ferasha-demo-2026")
        admin.email_verified_at = admin.date_joined
        admin.save()

    vendor, created = User.objects.get_or_create(
        email="karachi.mill@ferasha.com",
        defaults={"full_name": "Karachi Textile House", "role": UserRole.VENDOR},
    )
    if created:
        vendor.set_password("ferasha-demo-2026")
        vendor.save()

    # ----------------------------------------------------------- categories
    bridal = category("Bridal", "bridal", order=1)
    category("Lehenga", "lehenga", bridal, 1)
    sharara = category("Sharara & Gharara", "sharara-gharara", bridal, 2)
    suits = category("Suits", "suits", order=2)
    pakistani = category("Pakistani Suits", "pakistani-suits", suits, 1)
    category("Punjabi & Patiala", "punjabi-patiala", suits, 2)
    category("Lucknowi Chikankari", "lucknowi", suits, 3)

    # ------------------------------------------------------------- products
    # Deliberately spans the GST 2.0 Rs 2,500 per-piece slab boundary so the
    # tax engine's behaviour is visible in the preview.
    catalogue = [
        {
            "name": "Zardozi Bridal Lehenga - Deep Maroon",
            "slug": "zardozi-bridal-lehenga-maroon",
            "category": bridal,
            "garment_type": GarmentType.LEHENGA,
            "fabric": Fabric.RAW_SILK,
            "work_type": WorkType.ZARDOZI,
            "occasion": Occasion.BRIDAL,
            "base_price": Decimal("189000.00"),
            "hsn_code": "6204",
            "is_opaque": True,
            "has_full_lining": True,
            "slit_coverage": SlitCoverage.NONE,
            "sleeve_coverage": SleeveCoverage.FULL,
            "neckline_modesty": NecklineModesty.HIGH,
            "back_coverage": BackCoverage.FULL,
            "description": (
                "Hand-worked zardozi on raw silk, fully lined, with a six-metre "
                "kali flare. Approximately 400 hours of atelier work."
            ),
        },
        {
            "name": "Farshi Gharara - Ivory & Gold",
            "slug": "farshi-gharara-ivory-gold",
            "category": sharara,
            "garment_type": GarmentType.GHARARA,
            "fabric": Fabric.CHIFFON,
            "work_type": WorkType.GOTA_PATTI,
            "occasion": Occasion.BRIDAL,
            "base_price": Decimal("64500.00"),
            "hsn_code": "6204",
            "is_opaque": True,
            "has_full_lining": True,
            "slit_coverage": SlitCoverage.NONE,
            "sleeve_coverage": SleeveCoverage.THREE_QUARTER,
            "neckline_modesty": NecklineModesty.MODERATE,
            "back_coverage": BackCoverage.FULL,
            "description": "Traditional Lucknowi farshi silhouette with gota patti detailing.",
        },
        {
            "name": "Chikankari Kurta Set - Powder Blue",
            "slug": "chikankari-kurta-powder-blue",
            "category": pakistani,
            "garment_type": GarmentType.SUIT_SET,
            "fabric": Fabric.COTTON,
            "work_type": WorkType.CHIKANKARI,
            "occasion": Occasion.CASUAL,
            "base_price": Decimal("2350.00"),  # below the Rs 2,500 slab -> 5%
            "hsn_code": "6204",
            "is_opaque": True,
            "has_full_lining": False,
            "slit_coverage": SlitCoverage.KNEE,
            "sleeve_coverage": SleeveCoverage.THREE_QUARTER,
            "neckline_modesty": NecklineModesty.HIGH,
            "back_coverage": BackCoverage.FULL,
            "description": "Hand-embroidered Lucknowi chikankari on breathable cotton.",
        },
        {
            "name": "Organza Dupatta Suit - Blush",
            "slug": "organza-suit-blush",
            "category": pakistani,
            "garment_type": GarmentType.SUIT_SET,
            "fabric": Fabric.ORGANZA,
            "work_type": WorkType.RESHAM,
            "occasion": Occasion.EID,
            "base_price": Decimal("8900.00"),  # above the slab -> 18%
            "hsn_code": "6204",
            # Sheer organza sold WITHOUT lining, so the storefront must warn
            # rather than quietly badge it as modest.
            "is_opaque": False,
            "has_full_lining": False,
            "requires_slip": True,
            "slit_coverage": SlitCoverage.ANKLE,
            "sleeve_coverage": SleeveCoverage.FULL,
            "neckline_modesty": NecklineModesty.MODERATE,
            "back_coverage": BackCoverage.FULL,
            "description": "Sheer organza over a full crepe lining, with thread-work borders.",
        },
    ]

    for spec in catalogue:
        product, created = Product.objects.get_or_create(
            slug=spec["slug"],
            defaults={**spec, "vendor": vendor, "status": ProductStatus.ACTIVE},
        )
        if created:
            for size in (SizeStandard.S, SizeStandard.M, SizeStandard.L):
                ProductVariant.objects.create(
                    product=product,
                    sku=f"{product.slug[:12].upper()}-{size.value}",
                    size=size,
                    colour="As shown",
                    stock_quantity=6,
                )

    print(f"Categories : {Category.objects.count()}")
    print(f"Products   : {Product.objects.count()}")
    print(f"Variants   : {ProductVariant.objects.count()}")
    print(f"Users      : {User.objects.count()}")


if __name__ == "__main__":
    main()
