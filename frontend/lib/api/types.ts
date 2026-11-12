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

/** A publishable photo as list endpoints send it. */
export interface ImageRef {
  readonly url: string;
  readonly alt_text: string;
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
  /** Approved photos only (faces blurred); null until one exists. */
  readonly primary_image: ImageRef | null;
  /** A second angle, shown when the card is hovered or focused. */
  readonly secondary_image: ImageRef | null;
  readonly status: string;
  /** When the garment was listed (ISO 8601); drives the card's "New" label. */
  readonly created_at: string;
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

export type FitFeedback = "ran_small" | "true_to_size" | "ran_large";

/** A published review, as /reviews/ lists it. Only a first name is ever published. */
export interface Review {
  readonly id: string;
  readonly product: string;
  readonly author_name: string;
  readonly rating: number;
  readonly title: string;
  readonly body: string;
  readonly fit_feedback: FitFeedback | "";
  readonly modesty_as_described: boolean | null;
  /** Set by the server from a delivered order; a client cannot claim it. */
  readonly is_verified_purchase: boolean;
  readonly created_at: string;
}

/** /reviews/summary/?product=: published reviews only. */
export interface ReviewSummary {
  readonly count: number;
  readonly average: string | null;
  readonly distribution: Readonly<Record<"1" | "2" | "3" | "4" | "5", number>>;
  readonly fit: Readonly<Record<FitFeedback, number>>;
  readonly modesty_as_described: { readonly yes: number; readonly no: number };
}

export interface NewReview {
  readonly product: string;
  readonly rating: number;
  readonly title: string;
  readonly body: string;
  readonly fit_feedback: FitFeedback | "";
  readonly modesty_as_described: boolean | null;
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
  /** Made to measure: one piece, stitching surcharge included in unit_price. */
  readonly is_bespoke: boolean;
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
  readonly phone?: string;
  /** Staff or admin: may open the owner dashboard. Decided by the API, never here. */
  readonly is_back_office: boolean;
  /** False until the link in the welcome email is opened (Google sign-ins arrive verified). */
  readonly email_verified?: boolean;
}

/** Mirrors backend-core users.RegistrationSerializer. */
export interface Registration {
  readonly full_name: string;
  readonly email: string;
  readonly phone?: string;
  readonly password: string;
  /** Optional: the form shows the password instead of asking twice. */
  readonly password_confirm?: string;
  readonly accept_terms: boolean;
}

/** An outside sign-in switched on in Django (GET /auth/social/providers/). */
export interface SocialProvider {
  readonly id: string;
  readonly name: string;
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
  readonly is_bespoke: boolean;
}

/** A status change. `actor_name` and `reason` are sent to the back office only. */
export interface OrderEvent {
  readonly id: number;
  readonly from_status: string;
  readonly to_status: string;
  readonly actor_name?: string;
  readonly reason?: string;
  readonly created_at: string;
}

/** Mirrors backend-core orders.OrderListSerializer. */
export interface OrderSummary {
  readonly id: string;
  readonly order_number: string;
  readonly status: string;
  readonly currency: string;
  readonly grand_total: string;
  readonly line_count: number;
  /** "Velvet Gharara", or "Velvet Gharara and 2 more". */
  readonly item_summary: string;
  /** Back office only; empty for everyone else. */
  readonly customer_name: string;
  readonly placed_at: string | null;
  readonly created_at: string;
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
  readonly customer_name: string;
  readonly contact_email: string;
  readonly customer_notes: string;
  readonly events: readonly OrderEvent[];
  /** Where the back office may move it next; empty for anyone else. */
  readonly next_statuses: readonly string[];
}

/* ------------------------------------------------------------ back office */

/** Mirrors backend-core backoffice.services.dashboard_summary. */
export interface DashboardSummary {
  readonly currency: string;
  readonly revenue: { readonly month_to_date: string; readonly previous_period: string };
  readonly orders: { readonly month_to_date: number; readonly previous_period: number };
  readonly average_order_value: string | null;
  readonly series: readonly { readonly date: string; readonly revenue: string; readonly orders: number }[];
  /** Every open stage in working order, empty ones included. */
  readonly pipeline: readonly { readonly status: string; readonly label: string; readonly count: number }[];
  readonly moderation: { readonly reviews_pending: number; readonly photos_needing_review: number };
  readonly low_stock: readonly {
    readonly sku: string;
    readonly product_name: string;
    readonly product_slug: string;
    readonly size: string;
    readonly colour: string;
    readonly stock_quantity: number;
  }[];
  readonly recent_orders: readonly OrderSummary[];
}
