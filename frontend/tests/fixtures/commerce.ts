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
};

export const BAG: CartItem[] = [
  { variantId: "v-m-ivory", name: PRODUCT.name, price: 12000, quantity: 1, image: "", colour: "Ivory", size: "M" },
  { variantId: "v-m-sage", name: PRODUCT.name, price: 12500, quantity: 2, image: "", colour: "Sage", size: "M" },
];
