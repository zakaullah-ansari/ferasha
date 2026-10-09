/**
 * Types mirroring the Phase 2 DRF serializers.
 *
 * Hand-written for the surfaces the storefront actually consumes rather than
 * generated wholesale from the OpenAPI schema: the generated client is a
 * build-step dependency on a running backend, which is the wrong trade for a
 * handful of read endpoints. `tests/api-contract.test.ts` validates these
 * shapes against live API responses so they cannot rot silently.
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

export interface ProductDetail extends ProductSummary {
  readonly description: string;
  readonly care_instructions: string;
  readonly variants: readonly ProductVariant[];
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
