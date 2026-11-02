"""Checkout: turn the customer's active cart into a placed order.

The server is the only party that prices an order. The client sends an address
and nothing else that affects money; subtotal, shipping and GST are recomputed
here from the catalogue on every quote and again at placement. A quote is
advisory, and the client may echo its ``grand_total`` back as
``expected_grand_total`` so a price change between quote and placement is
reported instead of silently charged.

Placement is one transaction: lock the cart, decrement stock, write the order,
its lines and its immutable tax snapshot, move it DRAFT -> PLACED, and retire
the cart. Any failure rolls all of it back.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cart.models import Cart, CartItem
from apps.catalog.enums import ProductStatus
from apps.catalog.models import ProductVariant
from apps.catalog.services import InsufficientStock, reserve_stock
from apps.orders.models import Order, OrderLine, OrderStatus, OrderTaxSnapshot
from apps.orders.state_machine import transition_order
from apps.taxes.services import (
    PlaceOfSupply,
    TaxableLine,
    TaxBreakdown,
    TaxError,
    calculate_gst,
    money,
)

#: Crockford base32 without I, L, O, U: unambiguous when read over the phone.
_ORDER_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class CheckoutError(ValueError):
    """The order cannot be placed as requested; the message is customer-safe."""


class PriceChanged(CheckoutError):
    """The total moved between quote and placement. Carries the fresh quote."""

    def __init__(self, quote: Quote) -> None:
        super().__init__("Prices have changed since your quote. Please review your order.")
        self.quote = quote


@dataclass(frozen=True)
class Quote:
    lines: tuple[CartItem, ...]
    place: PlaceOfSupply
    subtotal: Decimal
    shipping_charge: Decimal
    breakdown: TaxBreakdown

    @property
    def grand_total(self) -> Decimal:
        return self.breakdown.grand_total

    def as_dict(self) -> dict[str, Any]:
        return {
            "currency": settings.FERASHA_CURRENCY,
            "lines": [
                {
                    "variant_id": str(item.variant_id),
                    "sku": item.variant.sku,
                    "product_name": item.variant.product.name,
                    "variant_label": _variant_label(item.variant),
                    "quantity": item.quantity,
                    "unit_price": str(item.variant.price),
                    "line_total": str(item.variant.price * item.quantity),
                }
                for item in self.lines
            ],
            "subtotal": str(self.subtotal),
            "shipping_charge": str(self.shipping_charge),
            "tax": self.breakdown.as_dict(),
            "tax_total": str(self.breakdown.tax_total),
            "grand_total": str(self.grand_total),
        }


def _variant_label(variant: ProductVariant) -> str:
    return f"{variant.size} / {variant.colour}"


def shipping_charge_for(place: PlaceOfSupply) -> Decimal:
    """Delivery charge for a destination.

    International delivery is refused rather than guessed at: the tax engine
    can zero-rate an export, but there is no courier rate to charge for one.
    """
    if not place.is_domestic:
        raise CheckoutError("International delivery is not available yet.")
    if place.state_code == settings.FERASHA_HOME_STATE_CODE:
        return money(settings.FERASHA_SHIPPING_HOME_STATE)
    return money(settings.FERASHA_SHIPPING_DOMESTIC)


def _cart_lines(cart: Cart) -> tuple[CartItem, ...]:
    return tuple(
        cart.items.select_related("variant__product").order_by("variant_id")
    )


def _assert_purchasable(lines: tuple[CartItem, ...]) -> None:
    if not lines:
        raise CheckoutError("Your bag is empty.")
    for item in lines:
        variant = item.variant
        if not variant.is_active or variant.product.status != ProductStatus.ACTIVE:
            raise CheckoutError(f"{variant.product.name} is no longer available.")
        if variant.stock_quantity < item.quantity:
            raise CheckoutError(
                f"Only {max(variant.stock_quantity, 0)} of {variant.product.name} "
                f"({_variant_label(variant)}) left in stock."
            )


def _price(lines: tuple[CartItem, ...], address: dict[str, Any]) -> Quote:
    try:
        place = PlaceOfSupply(
            country_code=address["country_code"], state_code=address.get("state_code", "")
        )
    except TaxError as exc:
        raise CheckoutError(str(exc)) from exc

    shipping = shipping_charge_for(place)
    taxable = [
        TaxableLine(
            sku=item.variant.sku,
            hsn_code=item.variant.product.hsn_code,
            unit_price=item.variant.price,
            quantity=item.quantity,
            description=item.variant.product.name,
            rate_override=item.variant.product.gst_rate_override,
        )
        for item in lines
    ]
    try:
        breakdown = calculate_gst(
            taxable, place, shipping_charge=shipping, as_of=timezone.localdate()
        )
    except TaxError as exc:
        raise CheckoutError(str(exc)) from exc

    subtotal = money(sum((item.variant.price * item.quantity for item in lines), Decimal("0")))
    return Quote(
        lines=lines, place=place, subtotal=subtotal, shipping_charge=shipping, breakdown=breakdown
    )


def quote(user, address: dict[str, Any]) -> Quote:
    """Price the customer's active cart for delivery to ``address``. No side effects."""
    cart = Cart.objects.filter(user=user, is_active=True).first()
    lines = _cart_lines(cart) if cart else ()
    _assert_purchasable(lines)
    return _price(lines, address)


def _new_order_number() -> str:
    return "FER-" + "".join(secrets.choice(_ORDER_ALPHABET) for _ in range(10))


def _create_order(**fields) -> Order:
    # 32^10 numbers make a collision vanishingly rare, but the unique index is
    # the arbiter. A savepoint keeps a collision from poisoning the outer
    # transaction.
    for _ in range(5):
        try:
            with transaction.atomic():
                return Order.objects.create(order_number=_new_order_number(), **fields)
        except IntegrityError as exc:
            if "order_number" not in str(exc):
                raise
    raise CheckoutError("Could not allocate an order number. Please try again.")


@transaction.atomic
def place_order(
    user,
    address: dict[str, Any],
    *,
    expected_grand_total: Decimal | None = None,
    customer_notes: str = "",
) -> Order:
    """Convert the active cart into a PLACED order. All-or-nothing."""
    # Locking the cart serialises a double-submit: the second request waits,
    # then finds the cart retired and stops here.
    cart = Cart.objects.select_for_update().filter(user=user, is_active=True).first()
    if cart is None:
        raise CheckoutError("Your bag is empty.")

    lines = _cart_lines(cart)
    # Lock the variants in a fixed order (by id) so concurrent checkouts that
    # share items cannot deadlock, then re-read stock under the lock.
    locked = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product")
        .filter(pk__in=[item.variant_id for item in lines])
        .order_by("pk")
    }
    for item in lines:
        item.variant = locked[item.variant_id]

    _assert_purchasable(lines)
    priced = _price(lines, address)

    if expected_grand_total is not None and money(expected_grand_total) != priced.grand_total:
        raise PriceChanged(priced)

    for item in lines:
        try:
            reserve_stock(item.variant_id, item.quantity)
        except InsufficientStock as exc:
            raise CheckoutError(f"{item.variant.product.name} has just sold out.") from exc

    breakdown = priced.breakdown
    order = _create_order(
        customer=user,
        status=OrderStatus.DRAFT,
        place_of_supply_state=priced.place.state_code,
        place_of_supply_country=priced.place.country_code,
        supply_type=breakdown.supply_type.value,
        supply_date=timezone.localdate(),
        shipping_address=address,
        billing_address=address,
        customer_gstin=address.get("gstin", ""),
        currency=settings.FERASHA_CURRENCY,
        subtotal=priced.subtotal,
        shipping_charge=priced.shipping_charge,
        tax_total=breakdown.tax_total,
        grand_total=breakdown.grand_total,
        customer_notes=customer_notes,
    )

    OrderLine.objects.bulk_create(
        [
            OrderLine(
                order=order,
                variant=item.variant,
                sku=item.variant.sku,
                product_name=item.variant.product.name,
                variant_label=_variant_label(item.variant),
                hsn_code=item.variant.product.hsn_code,
                quantity=item.quantity,
                unit_price=item.variant.price,
                modesty_snapshot=item.variant.product.modesty.as_dict(),
            )
            for item in lines
        ]
    )

    OrderTaxSnapshot.objects.create(
        order=order,
        regime_name=breakdown.regime_name,
        supply_type=breakdown.supply_type.value,
        place_of_supply_state=priced.place.state_code,
        place_of_supply_country=priced.place.country_code,
        state_gst_code=priced.place.state_gst_code,
        taxable_value=breakdown.taxable_value,
        cgst_total=breakdown.cgst_total,
        sgst_total=breakdown.sgst_total,
        igst_total=breakdown.igst_total,
        tax_total=breakdown.tax_total,
        grand_total=breakdown.grand_total,
        is_zero_rated_export=breakdown.is_zero_rated_export,
        line_breakdown=breakdown.as_dict()["lines"],
        rate_summary=breakdown.as_dict()["rate_summary"],
        notes=list(breakdown.notes),
    )

    transition_order(order, OrderStatus.PLACED, actor=user, reason="Checkout")

    cart.is_active = False
    cart.save(update_fields=["is_active", "updated_at"])
    return order
