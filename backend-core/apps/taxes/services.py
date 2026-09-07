"""Ferasha GST engine.

Pure Python. No Django imports, no I/O, no floats. Every monetary value is a
``decimal.Decimal`` quantised to two places with ``ROUND_HALF_UP`` (the
rounding mode mandated by section 170 of the CGST Act).

Routing rules implemented
-------------------------
* Place of supply in Maharashtra (Ferasha's state of registration)
      -> intra-state supply -> CGST + SGST, each at half the applicable rate.
* Place of supply in any other Indian state / union territory
      -> inter-state supply -> IGST at the full applicable rate.
* Place of supply outside India
      -> zero-rated export under LUT/bond (IGST Act s.16). 0% tax.

Rate resolution
---------------
1. An explicit, validated per-line ``rate_override`` always wins.
2. Otherwise a flat-rated HSN/SAC (e.g. tailoring services at 18%) applies.
3. Otherwise the apparel value slab applies: 5% at or below Rs.1000 taxable
   value per piece, 12% above it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Iterable, Sequence

from .constants import (
    APPAREL_RATE_ABOVE_THRESHOLD,
    APPAREL_RATE_BELOW_THRESHOLD,
    APPAREL_SLAB_THRESHOLD,
    FLAT_RATE_HSN,
    INDIAN_STATE_GST_CODES,
    PERMITTED_GST_RATES,
    VALUE_SLABBED_HSN,
    ZERO_RATE,
)

TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")

HOME_STATE_CODE = "MH"
HOME_COUNTRY_CODE = "IN"


class TaxError(ValueError):
    """Raised when a supply cannot be taxed deterministically."""


class SupplyType(str, Enum):
    INTRA_STATE = "intra_state"
    INTER_STATE = "inter_state"
    EXPORT = "export"


def money(value: Decimal | int | str) -> Decimal:
    """Coerce to a 2dp Decimal using banker-free ROUND_HALF_UP."""
    try:
        return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:  # pragma: no cover - defensive
        raise TaxError(f"Cannot interpret {value!r} as a monetary amount.") from exc


def _normalise_country(code: str) -> str:
    code = (code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise TaxError(f"country_code must be an ISO 3166-1 alpha-2 code, got {code!r}.")
    return code


def _normalise_state(code: str) -> str:
    return (code or "").strip().upper()


@dataclass(frozen=True, slots=True)
class PlaceOfSupply:
    """Destination of the supply, derived from the customer's ship-to address."""

    country_code: str
    state_code: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "country_code", _normalise_country(self.country_code))
        object.__setattr__(self, "state_code", _normalise_state(self.state_code))
        if self.country_code == HOME_COUNTRY_CODE:
            if not self.state_code:
                raise TaxError("state_code is required for a place of supply within India.")
            if self.state_code not in INDIAN_STATE_GST_CODES:
                raise TaxError(f"Unknown Indian state/UT code {self.state_code!r}.")

    @property
    def is_domestic(self) -> bool:
        return self.country_code == HOME_COUNTRY_CODE

    @property
    def state_gst_code(self) -> str:
        return INDIAN_STATE_GST_CODES.get(self.state_code, "96") if self.is_domestic else "96"

    @property
    def supply_type(self) -> SupplyType:
        if not self.is_domestic:
            return SupplyType.EXPORT
        if self.state_code == HOME_STATE_CODE:
            return SupplyType.INTRA_STATE
        return SupplyType.INTER_STATE


@dataclass(frozen=True, slots=True)
class TaxableLine:
    """One sellable line: a garment, a bespoke tailoring charge, or shipping."""

    sku: str
    hsn_code: str
    unit_price: Decimal
    quantity: int = 1
    discount: Decimal = Decimal("0.00")
    description: str = ""
    #: Explicit rate as a whole-number percentage, e.g. Decimal("12").
    #: Set only where an HSN slab genuinely does not apply.
    rate_override: Decimal | None = None
    #: True when unit_price already contains GST (MRP-inclusive pricing).
    price_is_tax_inclusive: bool = False

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise TaxError(f"Line {self.sku!r}: quantity must be >= 1, got {self.quantity}.")
        unit_price = money(self.unit_price)
        if unit_price < 0:
            raise TaxError(f"Line {self.sku!r}: unit_price must not be negative.")
        discount = money(self.discount)
        if discount < 0:
            raise TaxError(f"Line {self.sku!r}: discount must not be negative.")
        gross = unit_price * self.quantity
        if discount > gross:
            raise TaxError(
                f"Line {self.sku!r}: discount {discount} exceeds line gross {gross}."
            )
        if not (self.hsn_code or "").strip():
            raise TaxError(f"Line {self.sku!r}: hsn_code is required.")
        object.__setattr__(self, "unit_price", unit_price)
        object.__setattr__(self, "discount", discount)
        object.__setattr__(self, "hsn_code", self.hsn_code.strip())
        if self.rate_override is not None:
            override = Decimal(self.rate_override)
            if override not in PERMITTED_GST_RATES:
                raise TaxError(
                    f"Line {self.sku!r}: rate_override {override} is not a lawful GST rate "
                    f"({sorted(PERMITTED_GST_RATES)})."
                )
            object.__setattr__(self, "rate_override", override)


@dataclass(frozen=True, slots=True)
class LineTax:
    """Immutable per-line tax result."""

    sku: str
    hsn_code: str
    quantity: int
    gross_amount: Decimal
    discount: Decimal
    taxable_value: Decimal
    gst_rate: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    line_total: Decimal
    rate_source: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "sku": self.sku,
            "hsn_code": self.hsn_code,
            "quantity": self.quantity,
            "gross_amount": str(self.gross_amount),
            "discount": str(self.discount),
            "taxable_value": str(self.taxable_value),
            "gst_rate": str(self.gst_rate),
            "cgst_rate": str(self.cgst_rate),
            "sgst_rate": str(self.sgst_rate),
            "igst_rate": str(self.igst_rate),
            "cgst_amount": str(self.cgst_amount),
            "sgst_amount": str(self.sgst_amount),
            "igst_amount": str(self.igst_amount),
            "total_tax": str(self.total_tax),
            "line_total": str(self.line_total),
            "rate_source": self.rate_source,
        }


@dataclass(frozen=True, slots=True)
class TaxBreakdown:
    """Order-level tax result. All amounts are 2dp Decimals."""

    place_of_supply: PlaceOfSupply
    supply_type: SupplyType
    lines: tuple[LineTax, ...]
    taxable_value: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    is_zero_rated_export: bool
    rate_summary: tuple[tuple[Decimal, Decimal, Decimal], ...] = field(default=())
    notes: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict[str, object]:
        return {
            "place_of_supply": {
                "country_code": self.place_of_supply.country_code,
                "state_code": self.place_of_supply.state_code,
                "state_gst_code": self.place_of_supply.state_gst_code,
            },
            "supply_type": self.supply_type.value,
            "lines": [line.as_dict() for line in self.lines],
            "taxable_value": str(self.taxable_value),
            "cgst_total": str(self.cgst_total),
            "sgst_total": str(self.sgst_total),
            "igst_total": str(self.igst_total),
            "tax_total": str(self.tax_total),
            "grand_total": str(self.grand_total),
            "is_zero_rated_export": self.is_zero_rated_export,
            "rate_summary": [
                {"rate": str(rate), "taxable_value": str(taxable), "tax": str(tax)}
                for rate, taxable, tax in self.rate_summary
            ],
            "notes": list(self.notes),
        }


def resolve_gst_rate(line: TaxableLine) -> tuple[Decimal, str]:
    """Resolve the applicable GST percentage for a line.

    Returns the whole-number rate and a short string naming its provenance,
    which is persisted on the invoice for audit purposes.
    """
    if line.rate_override is not None:
        return line.rate_override, "override"

    hsn = line.hsn_code
    if hsn in FLAT_RATE_HSN:
        return FLAT_RATE_HSN[hsn], f"flat:{hsn}"

    # Match on the 4-digit chapter heading so 6204.42.00 resolves like 6204.
    heading = hsn.replace(".", "")[:4]
    if heading in VALUE_SLABBED_HSN:
        per_piece = _per_piece_taxable_value(line)
        if per_piece <= APPAREL_SLAB_THRESHOLD:
            return APPAREL_RATE_BELOW_THRESHOLD, f"slab:{heading}:<=1000"
        return APPAREL_RATE_ABOVE_THRESHOLD, f"slab:{heading}:>1000"

    raise TaxError(
        f"Line {line.sku!r}: no GST rate could be resolved for HSN/SAC {hsn!r}. "
        "Register the code in apps.taxes.constants or set an explicit rate_override."
    )


def _per_piece_taxable_value(line: TaxableLine) -> Decimal:
    """Post-discount taxable value of a single piece.

    For tax-inclusive pricing the slab test is applied to the value net of tax.
    The slab itself depends on that net value, so we test the higher slab first
    and fall back - this converges because the two candidate rates are ordered.
    """
    net = (line.unit_price * line.quantity) - line.discount
    per_piece = money(net / line.quantity)
    if not line.price_is_tax_inclusive:
        return per_piece

    for rate in (APPAREL_RATE_ABOVE_THRESHOLD, APPAREL_RATE_BELOW_THRESHOLD):
        candidate = money(per_piece * HUNDRED / (HUNDRED + rate))
        above = candidate > APPAREL_SLAB_THRESHOLD
        if above == (rate == APPAREL_RATE_ABOVE_THRESHOLD):
            return candidate
    return money(per_piece * HUNDRED / (HUNDRED + APPAREL_RATE_BELOW_THRESHOLD))


def _taxable_value(line: TaxableLine, rate: Decimal) -> Decimal:
    """Assessable value for the whole line."""
    net = money((line.unit_price * line.quantity) - line.discount)
    if not line.price_is_tax_inclusive:
        return net
    return money(net * HUNDRED / (HUNDRED + rate))


def calculate_line_tax(line: TaxableLine, place_of_supply: PlaceOfSupply) -> LineTax:
    """Compute CGST/SGST/IGST for a single line at a given place of supply."""
    supply_type = place_of_supply.supply_type

    if supply_type is SupplyType.EXPORT:
        rate, rate_source = ZERO_RATE, "export:zero-rated"
    else:
        rate, rate_source = resolve_gst_rate(line)

    taxable_value = _taxable_value(line, rate)
    gross_amount = money(line.unit_price * line.quantity)

    cgst_rate = sgst_rate = igst_rate = ZERO_RATE
    if supply_type is SupplyType.INTRA_STATE:
        # Half to the Centre, half to Maharashtra.
        cgst_rate = sgst_rate = rate / Decimal("2")
    elif supply_type is SupplyType.INTER_STATE:
        igst_rate = rate

    cgst_amount = money(taxable_value * cgst_rate / HUNDRED)
    sgst_amount = money(taxable_value * sgst_rate / HUNDRED)
    igst_amount = money(taxable_value * igst_rate / HUNDRED)

    # For an odd rate (none exist today, but guard anyway) the halves must still
    # sum exactly to the total tax; absorb any rounding residue into SGST.
    if supply_type is SupplyType.INTRA_STATE:
        expected = money(taxable_value * rate / HUNDRED)
        residue = expected - (cgst_amount + sgst_amount)
        if residue:
            sgst_amount = money(sgst_amount + residue)

    total_tax = money(cgst_amount + sgst_amount + igst_amount)

    return LineTax(
        sku=line.sku,
        hsn_code=line.hsn_code,
        quantity=line.quantity,
        gross_amount=gross_amount,
        discount=line.discount,
        taxable_value=taxable_value,
        gst_rate=rate,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        igst_rate=igst_rate,
        cgst_amount=cgst_amount,
        sgst_amount=sgst_amount,
        igst_amount=igst_amount,
        total_tax=total_tax,
        line_total=money(taxable_value + total_tax),
        rate_source=rate_source,
    )


def calculate_gst(
    lines: Sequence[TaxableLine] | Iterable[TaxableLine],
    place_of_supply: PlaceOfSupply,
    *,
    shipping_charge: Decimal | str | int = Decimal("0.00"),
) -> TaxBreakdown:
    """Calculate the full GST breakdown for an order.

    ``shipping_charge`` is treated as part of a composite supply and is taxed at
    the highest rate present among the goods lines, per CGST Act s.8(a). If the
    order has no taxable goods the shipping charge is taxed at 18%.
    """
    lines = tuple(lines)
    if not lines:
        raise TaxError("At least one taxable line is required.")

    computed = [calculate_line_tax(line, place_of_supply) for line in lines]

    shipping = money(shipping_charge)
    if shipping < 0:
        raise TaxError("shipping_charge must not be negative.")

    notes: list[str] = []
    if shipping > 0:
        principal_rate = max((c.gst_rate for c in computed), default=Decimal("18"))
        shipping_line = TaxableLine(
            sku="SHIPPING",
            hsn_code="996812",
            unit_price=shipping,
            quantity=1,
            description="Delivery charges (composite supply)",
            rate_override=principal_rate if principal_rate in PERMITTED_GST_RATES else None,
        )
        if shipping_line.rate_override is None:  # pragma: no cover - defensive
            shipping_line = replace(shipping_line, rate_override=Decimal("18"))
        computed.append(calculate_line_tax(shipping_line, place_of_supply))
        notes.append(
            "Delivery charge taxed at the principal supply rate as a composite supply."
        )

    taxable_value = money(sum((c.taxable_value for c in computed), Decimal("0.00")))
    cgst_total = money(sum((c.cgst_amount for c in computed), Decimal("0.00")))
    sgst_total = money(sum((c.sgst_amount for c in computed), Decimal("0.00")))
    igst_total = money(sum((c.igst_amount for c in computed), Decimal("0.00")))
    tax_total = money(cgst_total + sgst_total + igst_total)

    supply_type = place_of_supply.supply_type
    if supply_type is SupplyType.EXPORT:
        notes.append(
            "Zero-rated export of goods under IGST Act s.16 - supply against LUT "
            "without payment of integrated tax."
        )
    elif supply_type is SupplyType.INTRA_STATE:
        notes.append("Intra-state supply within Maharashtra - CGST and SGST levied.")
    else:
        notes.append(
            f"Inter-state supply to state code {place_of_supply.state_gst_code} - IGST levied."
        )

    buckets: dict[Decimal, list[Decimal]] = {}
    for c in computed:
        bucket = buckets.setdefault(c.gst_rate, [Decimal("0.00"), Decimal("0.00")])
        bucket[0] += c.taxable_value
        bucket[1] += c.total_tax

    rate_summary = tuple(
        (rate, money(values[0]), money(values[1]))
        for rate, values in sorted(buckets.items())
    )

    return TaxBreakdown(
        place_of_supply=place_of_supply,
        supply_type=supply_type,
        lines=tuple(computed),
        taxable_value=taxable_value,
        cgst_total=cgst_total,
        sgst_total=sgst_total,
        igst_total=igst_total,
        tax_total=tax_total,
        grand_total=money(taxable_value + tax_total),
        is_zero_rated_export=supply_type is SupplyType.EXPORT,
        rate_summary=rate_summary,
        notes=tuple(notes),
    )
