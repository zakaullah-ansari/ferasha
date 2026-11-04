/**
 * Types mirroring the Phase 2 DRF serializers.
 *
 * Hand-written for the surfaces the storefront actually consumes rather than
 * generated wholesale from the OpenAPI schema: the generated client is a
 * build-step dependency on a running backend, which is the wrong trade for a
 * handful of read endpoints.
 *
 * Nothing yet checks these against live API responses, so they can drift from
 * the serializers silently. The shared fixtures in tests/fixtures/commerce.ts
 * are typed against them, which catches drift on this side only.
 */

/** A modesty badge or advisory, as derived by the Phase 1 backend. */
export interface ModestyFacet {
  readonly code: string;
  readonly label: string;
}

/**
 * Modesty disclosure block.
 *
 * `advisories` is the honest part: it lists reasons a garment may not meet a
 * customer's expectations. It is never filtered or hidden in the UI.
 */
export interface Modesty {
  readonly badges: readonly ModestyFacet[];
  readonly advisories: readonly ModestyFacet[];
  readonly coverage_score: number;
}

export interface ProductVariant {
  readonly id: string;
  readonly sku: string;
  readonly size: string;
  readonly colour: string;
  readonly colour_hex: string;
  readonly price: string;
  readonly price_delta: string;
  /**
   * Note what is absent: `stock_quantity`. The API exposes only a boolean, so
   * competitors cannot scrape inventory depth. The frontend therefore cannot
   * display "only 2 left" — by design, not by omission.
   */
  readonly in_stock: boolean;
  readonly is_active: boolean;
}

export interface ProductSummary {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly category_slug: string;
  readonly garment_type: string;
  readonly fabric: string;
  readonly work_type: string;
  readonly occasion: string;
  readonly base_price: string;
  readonly from_price: number;
  readonly compare_at_price: string | null;
  readonly supports_bespoke: boolean;
  readonly stitching_days: number;
  readonly modesty: Modesty;
  readonly primary_image: string | null;
  readonly status: string;
}

/** A publishable image: `url` is null unless the privacy pipeline approved it. */
export interface ProductImage {
  readonly id: string;
  readonly url: string | null;
  readonly alt_text: string;
  readonly display_order: number;
  readonly is_primary: boolean;
}

/* Coverage scales, least to most covering - mirror backend-core catalog/enums.py. */
export type NecklineModesty = "deep" | "moderate" | "high" | "closed";
export type SleeveCoverage =
  | "sleeveless" | "cap" | "short" | "elbow" | "three_quarter" | "full" | "extra_long";
export type BackCoverage = "open" | "deep" | "moderate" | "full";
export type SlitCoverage = "thigh" | "knee" | "mid_calf" | "ankle" | "none";

export interface ProductDetail extends ProductSummary {
  readonly description: string;
  readonly care_instructions: string;
  readonly variants: readonly ProductVariant[];
  readonly category: { readonly name: string; readonly slug: string };
  readonly images: readonly ProductImage[];
  readonly neckline_modesty: NecklineModesty;
  readonly sleeve_coverage: SleeveCoverage;
  readonly back_coverage: BackCoverage;
  readonly slit_coverage: SlitCoverage;
  readonly is_opaque: boolean;
  readonly has_full_lining: boolean;
  readonly requires_slip: boolean;
  readonly is_sheer_overlay_only: boolean;
  readonly rating_average: number | null;
  readonly rating_count: number;
  readonly bespoke_surcharge: string;
}

/** One option of a filter facet, with how many garments it would show. */
export interface FacetOption {
  readonly value: string;
  readonly label: string;
  readonly count: number;
}

/**
 * Filter counts for the current selection (/catalog/products/facets/).
 *
 * A facet's counts ignore its own selection but follow every other one, so
 * picking Eid keeps Bridal in view with the number it would add.
 */
export interface Facets {
  readonly occasion: readonly FacetOption[];
  readonly garment_type: readonly FacetOption[];
  readonly fabric: readonly FacetOption[];
  readonly work_type: readonly FacetOption[];
  readonly slit_coverage: readonly FacetOption[];
  readonly sleeve_coverage: readonly FacetOption[];
  /** Always all five modesty switches, including those with no garments. */
  readonly modesty: readonly FacetOption[];
  readonly supports_bespoke: number;
  readonly total: number;
}

export interface Category {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly description: string;
}

export interface Paginated<T> {
  readonly count: number;
  readonly next: string | null;
  readonly previous: string | null;
  readonly results: readonly T[];
}

export interface TaxLine {
  readonly sku: string;
  readonly hsn_code: string;
  readonly quantity: number;
  readonly taxable_value: string;
  readonly gst_rate: string;
  readonly cgst_amount: string;
  readonly sgst_amount: string;
  readonly igst_amount: string;
  readonly total_tax: string;
  readonly line_total: string;
  readonly rate_source: string;
}

export interface TaxQuote {
  readonly supply_type: "intra_state" | "inter_state" | "export";
  readonly lines: readonly TaxLine[];
  readonly taxable_value: string;
  readonly cgst_total: string;
  readonly sgst_total: string;
  readonly igst_total: string;
  readonly tax_total: string;
  readonly grand_total: string;
  readonly is_zero_rated_export: boolean;
  readonly regime: string;
  readonly notes: readonly string[];
}

/* ------------------------------------------------------------- checkout */

/** Mirrors backend-core checkout.DeliveryAddressSerializer. */
export interface DeliveryAddress {
  readonly recipient_name: string;
  readonly phone: string;
  readonly line1: string;
  readonly line2?: string;
  readonly city: string;
  /** ISO 3166-2:IN code without the "IN-" prefix, e.g. "MH". */
  readonly state_code: string;
  readonly postal_code: string;
  readonly country_code: string;
  readonly gstin?: string;
}

export interface CheckoutQuoteLine {
  readonly variant_id: string;
  readonly sku: string;
  readonly product_name: string;
  readonly variant_label: string;
  readonly quantity: number;
  readonly unit_price: string;
  readonly line_total: string;
}

/** Server-priced. Money fields are decimal strings; never recompute them here. */
export interface CheckoutQuote {
  readonly currency: string;
  readonly lines: readonly CheckoutQuoteLine[];
  readonly subtotal: string;
  readonly shipping_charge: string;
  readonly tax: TaxQuote;
  readonly tax_total: string;
  readonly grand_total: string;
}

export interface PlacedOrder {
  readonly order_number: string;
  readonly status: string;
  readonly grand_total: string;
  readonly currency: string;
}

/* -------------------------------------------------------------- session */

export interface SessionUser {
  readonly id: string;
  readonly email: string;
  readonly full_name: string;
}

/** Mirrors backend-core users.RegistrationSerializer. */
export interface Registration {
  readonly full_name: string;
  readonly email: string;
  readonly phone?: string;
  readonly password: string;
  readonly password_confirm: string;
  readonly accept_terms: boolean;
}

/* --------------------------------------------------------------- orders */

export interface OrderLine {
  readonly id: string;
  readonly sku: string;
  readonly product_name: string;
  readonly variant_label: string;
  readonly quantity: number;
  readonly unit_price: string;
  readonly gross: string;
}

/** Mirrors backend-core orders.OrderDetailSerializer (fields used here). */
export interface OrderDetail {
  readonly order_number: string;
  readonly status: string;
  readonly currency: string;
  readonly supply_type: "intra_state" | "inter_state" | "export";
  readonly shipping_address: DeliveryAddress;
  readonly subtotal: string;
  readonly shipping_charge: string;
  readonly tax_total: string;
  readonly grand_total: string;
  readonly lines: readonly OrderLine[];
  readonly tax_snapshot: {
    readonly cgst_total: string;
    readonly sgst_total: string;
    readonly igst_total: string;
  } | null;
  readonly placed_at: string | null;
}
