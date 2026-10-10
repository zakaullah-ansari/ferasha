"""Seed a representative Ferasha catalogue for local demonstration.

Deliberately includes garments that are *not* fully modest - a sheer organza
overlay, a deep-back blouse - because the point of the modesty attributes is
honest disclosure, not flattery. A catalogue where every product scores
perfectly would prove nothing about the advisory engine.

Idempotent: running it twice leaves the same data.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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

User = get_user_model()

# HSN 6204 covers women's suits, ensembles and dresses. The GST slab is
# resolved from the per-piece price at quote time, so both sides of the
# 2,500 rupee boundary are represented below.
HSN_SUITS = "6204"
HSN_BLOUSE = "6206"

CATEGORIES = [
    ("pakistani-suits", "Pakistani Suits", None),
    ("karachi-suits", "Karachi Suits", "pakistani-suits"),
    ("punjabi-suits", "Punjabi Suits", None),
    ("bridal", "Bridal", None),
    ("lehengas", "Lehengas", "bridal"),
    ("sharara-gharara", "Sharara & Gharara", "bridal"),
    ("blouses-jackets", "Blouses & Jackets", None),
]

PRODUCTS = [
    {
        "slug": "karachi-lawn-chikankari-ivory",
        "name": "Karachi Lawn Chikankari Suit - Ivory",
        "category": "karachi-suits",
        "garment_type": GarmentType.SUIT_SET,
        "fabric": Fabric.LAWN,
        "work_type": WorkType.CHIKANKARI,
        "occasion": Occasion.CASUAL,
        "base_price": Decimal("2350.00"),
        "hsn_code": HSN_SUITS,
        "description": (
            "Hand-worked chikankari on fine Karachi lawn. Three-piece set with "
            "a full-length kameez, straight trousers and a matching dupatta."
        ),
        "care_instructions": "Hand wash cold. Dry in shade. Warm iron on reverse.",
        "is_opaque": True,
        "has_full_lining": True,
        "slit_coverage": SlitCoverage.ANKLE,
        "sleeve_coverage": SleeveCoverage.FULL,
        "neckline_modesty": NecklineModesty.HIGH,
        "back_coverage": BackCoverage.FULL,
        "requires_slip": False,
        "is_sheer_overlay_only": False,
        "supports_bespoke": True,
        "bespoke_surcharge": Decimal("850.00"),
        "stitching_days": 12,
        "variants": [
            ("KAR-LWN-IVR-S", SizeStandard.S, "Ivory", "#F4F0E6", 6),
            ("KAR-LWN-IVR-M", SizeStandard.M, "Ivory", "#F4F0E6", 9),
            ("KAR-LWN-IVR-L", SizeStandard.L, "Ivory", "#F4F0E6", 4),
        ],
    },
    {
        "slug": "organza-suit-blush",
        "name": "Organza Sequin Suit - Blush",
        "category": "pakistani-suits",
        "garment_type": GarmentType.SUIT_SET,
        "fabric": Fabric.ORGANZA,
        "work_type": WorkType.SEQUIN,
        "occasion": Occasion.PARTY,
        "base_price": Decimal("6800.00"),
        "hsn_code": HSN_SUITS,
        "description": (
            "Sequinned organza kameez with a scalloped hem. The organza is a "
            "sheer overlay and is supplied unlined; a slip is required."
        ),
        "care_instructions": "Dry clean only.",
        # Honest disclosure. This garment is sheer, and the API says so.
        "is_opaque": False,
        "has_full_lining": False,
        "slit_coverage": SlitCoverage.THIGH,
        "sleeve_coverage": SleeveCoverage.THREE_QUARTER,
        "neckline_modesty": NecklineModesty.MODERATE,
        "back_coverage": BackCoverage.MODERATE,
        "requires_slip": True,
        "is_sheer_overlay_only": True,
        "supports_bespoke": True,
        "bespoke_surcharge": Decimal("1200.00"),
        "stitching_days": 18,
        "variants": [
            ("ORG-SEQ-BLS-S", SizeStandard.S, "Blush", "#E8C4C0", 3),
            ("ORG-SEQ-BLS-M", SizeStandard.M, "Blush", "#E8C4C0", 5),
        ],
    },
    {
        "slug": "banarasi-bridal-lehenga-crimson",
        "name": "Banarasi Bridal Lehenga - Crimson",
        "category": "lehengas",
        "garment_type": GarmentType.LEHENGA,
        "fabric": Fabric.BANARASI,
        "work_type": WorkType.ZARDOZI,
        "occasion": Occasion.BRIDAL,
        "base_price": Decimal("84500.00"),
        "hsn_code": HSN_SUITS,
        "description": (
            "Handloom Banarasi silk lehenga with zardozi and dabka work across "
            "the ghera. Fully lined and canvassed, with a six-metre dupatta."
        ),
        "care_instructions": "Specialist dry clean only. Store flat in muslin.",
        "is_opaque": True,
        "has_full_lining": True,
        "slit_coverage": SlitCoverage.NONE,
        "sleeve_coverage": SleeveCoverage.ELBOW,
        "neckline_modesty": NecklineModesty.MODERATE,
        "back_coverage": BackCoverage.MODERATE,
        "requires_slip": False,
        "is_sheer_overlay_only": False,
        "supports_bespoke": True,
        "bespoke_surcharge": Decimal("15000.00"),
        "stitching_days": 45,
        "variants": [
            ("BAN-LHG-CRM-M", SizeStandard.M, "Crimson", "#8B1A1A", 1),
            ("BAN-LHG-CRM-L", SizeStandard.L, "Crimson", "#8B1A1A", 1),
            ("BAN-LHG-CRM-CUS", SizeStandard.CUSTOM, "Crimson", "#8B1A1A", 0),
        ],
    },
    {
        "slug": "velvet-gharara-emerald",
        "name": "Velvet Gharara Set - Emerald",
        "category": "sharara-gharara",
        "garment_type": GarmentType.GHARARA,
        "fabric": Fabric.VELVET,
        "work_type": WorkType.GOTA_PATTI,
        "occasion": Occasion.NIKAH,
        "base_price": Decimal("42000.00"),
        "hsn_code": HSN_SUITS,
        "description": (
            "Emerald velvet gharara with gota patti detailing at the knee "
            "joint, worn with a short kurti and tissue dupatta."
        ),
        "care_instructions": "Dry clean only. Do not fold along the gota.",
        "is_opaque": True,
        "has_full_lining": True,
        "slit_coverage": SlitCoverage.NONE,
        "sleeve_coverage": SleeveCoverage.FULL,
        "neckline_modesty": NecklineModesty.HIGH,
        "back_coverage": BackCoverage.FULL,
        "requires_slip": False,
        "is_sheer_overlay_only": False,
        "supports_bespoke": True,
        "bespoke_surcharge": Decimal("6500.00"),
        "stitching_days": 30,
        "variants": [
            ("VEL-GHR-EMR-S", SizeStandard.S, "Emerald", "#0B6B4F", 2),
            ("VEL-GHR-EMR-M", SizeStandard.M, "Emerald", "#0B6B4F", 2),
        ],
    },
    {
        "slug": "raw-silk-blouse-gold",
        "name": "Raw Silk Deep-Back Blouse - Antique Gold",
        "category": "blouses-jackets",
        "garment_type": GarmentType.BLOUSE,
        "fabric": Fabric.RAW_SILK,
        "work_type": WorkType.RESHAM,
        "occasion": Occasion.WALIMA,
        "base_price": Decimal("4200.00"),
        "hsn_code": HSN_BLOUSE,
        "description": (
            "Raw silk blouse with resham embroidery and a deep scooped back "
            "finished with a tassel tie."
        ),
        "care_instructions": "Dry clean recommended.",
        "is_opaque": True,
        "has_full_lining": True,
        # Deep back: disclosed rather than hidden, so the advisory can fire.
        "slit_coverage": SlitCoverage.NONE,
        "sleeve_coverage": SleeveCoverage.SHORT,
        "neckline_modesty": NecklineModesty.MODERATE,
        "back_coverage": BackCoverage.DEEP,
        "requires_slip": False,
        "is_sheer_overlay_only": False,
        "supports_bespoke": True,
        "bespoke_surcharge": Decimal("900.00"),
        "stitching_days": 14,
        "variants": [
            ("RAW-BLS-GLD-S", SizeStandard.S, "Antique Gold", "#C9A227", 7),
            ("RAW-BLS-GLD-M", SizeStandard.M, "Antique Gold", "#C9A227", 0),
        ],
    },
    {
        "slug": "chanderi-punjabi-suit-powder-blue",
        "name": "Chanderi Punjabi Patiala Suit - Powder Blue",
        "category": "punjabi-suits",
        "garment_type": GarmentType.SUIT_SET,
        "fabric": Fabric.COTTON,
        "work_type": WorkType.PRINTED,
        "occasion": Occasion.EID,
        "base_price": Decimal("1890.00"),
        "hsn_code": HSN_SUITS,
        "description": (
            "Block-printed cotton kameez with a full Patiala salwar and "
            "chiffon dupatta. An everyday Eid staple."
        ),
        "care_instructions": "Machine wash gentle, cold. Line dry.",
        "is_opaque": True,
        "has_full_lining": False,
        "slit_coverage": SlitCoverage.KNEE,
        "sleeve_coverage": SleeveCoverage.THREE_QUARTER,
        "neckline_modesty": NecklineModesty.HIGH,
        "back_coverage": BackCoverage.FULL,
        "requires_slip": False,
        "is_sheer_overlay_only": False,
        "supports_bespoke": False,
        "bespoke_surcharge": Decimal("0.00"),
        "stitching_days": 7,
        "variants": [
            ("CHN-PTL-PBL-M", SizeStandard.M, "Powder Blue", "#AFC7DB", 12),
            ("CHN-PTL-PBL-L", SizeStandard.L, "Powder Blue", "#AFC7DB", 8),
            ("CHN-PTL-PBL-XL", SizeStandard.XL, "Powder Blue", "#AFC7DB", 5),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a representative catalogue for local demonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        vendor, created = User.objects.get_or_create(
            email="atelier@ferasha.com",
            defaults={
                "full_name": "Ferasha Atelier",
                "role": "vendor",
                "is_staff": True,
            },
        )
        if created:
            vendor.set_password("demo-atelier-password")
            vendor.save(update_fields=["password"])

        categories: dict[str, Category] = {}
        for slug, name, parent_slug in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "parent": categories.get(parent_slug)},
            )
            categories[slug] = category

        created_products = 0
        for spec in PRODUCTS:
            spec = dict(spec)
            variants = spec.pop("variants")
            category = categories[spec.pop("category")]

            product, made = Product.objects.update_or_create(
                slug=spec.pop("slug"),
                defaults={
                    **spec,
                    "category": category,
                    "vendor": vendor,
                    "status": ProductStatus.ACTIVE,
                    "published_at": timezone.now(),
                },
            )
            created_products += int(made)

            for sku, size, colour, colour_hex, stock in variants:
                ProductVariant.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "product": product,
                        "size": size,
                        "colour": colour,
                        "colour_hex": colour_hex,
                        "stock_quantity": stock,
                        "weight_grams": 900,
                        "is_active": True,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Product.objects.count()} products "
                f"({created_products} new), "
                f"{ProductVariant.objects.count()} variants, "
                f"{Category.objects.count()} categories."
            )
        )
