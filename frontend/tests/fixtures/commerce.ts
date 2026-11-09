/**
 * Realistic commerce data shared by unit tests and Storybook stories.
 *
 * Typed against the API types, so a change to a response shape breaks these
 * at compile time instead of leaving stories that render stale data.
 * Figures match backend-core's GST engine: a Rs.12,000 suit (HSN 6204, 18%
 * GST 2.0 slab) to Mumbai is CGST 1,080 + SGST 1,080 = 14,160.
 */

import type {
  CheckoutQuote,
  Facets,
  PlacedOrder,
  ProductDetail,
  SessionUser,
} from "@/lib/api/types";
import type { CartItem } from "@/store/useCartStore";

export const MODESTY_FULL = {
  coverage_score: 92,
  badges: [
    { code: "fully_lined", label: "Fully lined" },
    { code: "opaque_fabric", label: "Opaque fabric" },
    { code: "full_sleeves", label: "Full sleeves" },
    { code: "modest_neckline", label: "Modest neckline" },
  ],
  advisories: [],
} as const;

export const PRODUCT: ProductDetail = {
  id: "8d1f4c1e-0000-4000-8000-000000000001",
  slug: "karachi-lawn-chikankari-ivory",
  name: "Karachi Lawn Chikankari - Ivory",
  category_slug: "pakistani-suits",
  garment_type: "suit_set",
  fabric: "lawn",
  work_type: "chikankari",
  occasion: "eid",
  base_price: "12000.00",
  from_price: 12000,
  compare_at_price: null,
  supports_bespoke: true,
  stitching_days: 10,
  modesty: MODESTY_FULL,
  primary_image: null,
  status: "active",
  description: "Hand-worked chikankari on fine Karachi lawn. Three-piece set.",
  care_instructions: "Dry clean only.",
  category: { name: "Karachi Suits", slug: "karachi-suits" },
  images: [],
  neckline_modesty: "high",
  sleeve_coverage: "full",
  back_coverage: "full",
  slit_coverage: "ankle",
  is_opaque: true,
  has_full_lining: true,
  requires_slip: false,
  is_sheer_overlay_only: false,
  rating_average: null,
  rating_count: 0,
  bespoke_surcharge: "1500.00",
  variants: [
    { id: "v-s-ivory", sku: "KLC-IV-S", size: "S", colour: "Ivory", colour_hex: "#F4EFE6", price: "12000.00", price_delta: "0.00", in_stock: true, is_active: true },
    { id: "v-m-ivory", sku: "KLC-IV-M", size: "M", colour: "Ivory", colour_hex: "#F4EFE6", price: "12000.00", price_delta: "0.00", in_stock: true, is_active: true },
    { id: "v-l-ivory", sku: "KLC-IV-L", size: "L", colour: "Ivory", colour_hex: "#F4EFE6", price: "12000.00", price_delta: "0.00", in_stock: false, is_active: true },
    { id: "v-m-sage", sku: "KLC-SG-M", size: "M", colour: "Sage", colour_hex: "#9CAF88", price: "12500.00", price_delta: "500.00", in_stock: true, is_active: true },
  ],
};

export const QUOTE: CheckoutQuote = {
  currency: "INR",
  lines: [
    {
      variant_id: "v-m-ivory",
      sku: "KLC-IV-M",
      product_name: PRODUCT.name,
      variant_label: "M / Ivory",
      quantity: 1,
      is_bespoke: false,
      unit_price: "12000.00",
      line_total: "12000.00",
    },
  ],
  subtotal: "12000.00",
  shipping_charge: "0.00",
  tax: {
    supply_type: "intra_state",
    lines: [],
    taxable_value: "12000.00",
    cgst_total: "1080.00",
    sgst_total: "1080.00",
    igst_total: "0.00",
    tax_total: "2160.00",
    grand_total: "14160.00",
    is_zero_rated_export: false,
    regime: "GST 2.0",
    notes: [],
  },
  tax_total: "2160.00",
  grand_total: "14160.00",
};

export const ORDER: PlacedOrder = {
  order_number: "FER-ABC123",
  status: "placed",
  grand_total: "14160.00",
  currency: "INR",
};

export const CUSTOMER: SessionUser = {
  id: "u-1",
  email: "ayesha@example.com",
  full_name: "Ayesha Khan",
  is_back_office: false,
};

export const BAG: CartItem[] = [
  { lineId: "v-m-ivory", variantId: "v-m-ivory", name: PRODUCT.name, price: 12000, quantity: 1, image: "", colour: "Ivory", size: "M" },
  { lineId: "v-m-sage", variantId: "v-m-sage", name: PRODUCT.name, price: 12500, quantity: 2, image: "", colour: "Sage", size: "M" },
];

/** Filter counts for the whole catalogue, as /catalog/products/facets/ returns them. */
export const FACETS: Facets = {
  occasion: [
    { value: "bridal", label: "Bridal", count: 3 },
    { value: "nikah", label: "Nikah", count: 1 },
    { value: "walima", label: "Walima", count: 1 },
    { value: "eid", label: "Eid", count: 1 },
    { value: "party", label: "Party", count: 1 },
    { value: "casual", label: "Casual / Daily", count: 2 },
  ],
  garment_type: [
    { value: "suit_set", label: "Suit / Kameez set", count: 4 },
    { value: "lehenga", label: "Lehenga", count: 2 },
    { value: "gharara", label: "Gharara", count: 2 },
    { value: "blouse", label: "Blouse", count: 1 },
  ],
  fabric: [
    { value: "lawn", label: "Lawn", count: 1 },
    { value: "chiffon", label: "Chiffon", count: 1 },
    { value: "raw_silk", label: "Raw silk", count: 2 },
    { value: "velvet", label: "Velvet", count: 1 },
    { value: "cotton", label: "Cotton", count: 2 },
  ],
  work_type: [
    { value: "zardozi", label: "Zardozi", count: 2 },
    { value: "gota_patti", label: "Gota patti", count: 2 },
    { value: "chikankari", label: "Chikankari", count: 2 },
  ],
  slit_coverage: [{ value: "none", label: "No slit", count: 5 }],
  sleeve_coverage: [{ value: "full", label: "Full length", count: 5 }],
  modesty: [
    { value: "fully_covered", label: "Fully covered", count: 4 },
    { value: "has_full_lining", label: "Fully lined", count: 6 },
    { value: "is_opaque", label: "Opaque fabric", count: 7 },
    { value: "full_sleeves", label: "Full sleeves", count: 5 },
    { value: "no_slit", label: "No slit", count: 0 },
  ],
  supports_bespoke: 5,
  total: 9,
};

/** A made-to-measure piece in the bag: one line per piece, surcharge included in its price. */
export const BESPOKE_LINE: CartItem = {
  lineId: "bespoke-1",
  variantId: "v-custom",
  name: PRODUCT.name,
  price: 15000,
  quantity: 1,
  image: "",
  colour: "Ivory",
  size: "CUSTOM",
  bespoke: {
    measurements: { bust: 36, waist: 30, hip: 38, shoulder: 14, kameez_length: 42, sleeve_length: 22 },
    preferences: { lining_preference: "full" },
  },
};
