/**
 * Owner dashboard data shared by unit tests and stories. Typed against the API
 * types; figures follow the commerce fixtures (a Rs.14,160 suit to Mumbai).
 */

import type { DashboardSummary, OrderDetail, OrderSummary } from "@/lib/api/types";

/** Thirty days to 20 Nov 2026, deterministic so stories and screenshots are stable. */
const SERIES = Array.from({ length: 30 }, (_, index) => {
  const day = new Date(Date.UTC(2026, 9, 22 + index));
  const orders = [0, 1, 0, 2, 1, 0, 0, 3, 1, 0][index % 10]!;
  return { date: day.toISOString().slice(0, 10), revenue: (orders * 14160).toFixed(2), orders };
});

export const RECENT_ORDERS: OrderSummary[] = [
  ["FER-260412", "payment_confirmed", "Ayesha Khan", "14160.00", 1],
  ["FER-260411", "stitching", "Sana Mir", "84500.00", 2],
  ["FER-260409", "packed", "Hina Qureshi", "4200.00", 1],
  ["FER-260406", "shipped", "Zoya Shaikh", "189000.00", 3],
  ["FER-260402", "placed", "guest@example.com", "6800.00", 1],
  ["FER-260398", "delivered", "Mehreen Ansari", "42000.00", 1],
].map(([order_number, status, customer_name, grand_total, line_count], index) => ({
  id: `order-${index}`,
  order_number: order_number as string,
  status: status as string,
  currency: "INR",
  grand_total: grand_total as string,
  line_count: line_count as number,
  item_summary: line_count === 1 ? "Karachi Lawn Chikankari - Ivory" : `Velvet Gharara - Emerald and ${(line_count as number) - 1} more`,
  customer_name: customer_name as string,
  placed_at: `2026-11-${String(20 - index * 2).padStart(2, "0")}T08:50:00Z`,
  created_at: `2026-11-${String(20 - index * 2).padStart(2, "0")}T08:45:00Z`,
}));

export const SUMMARY: DashboardSummary = {
  currency: "INR",
  revenue: { month_to_date: "325680.00", previous_period: "254880.00" },
  orders: { month_to_date: 23, previous_period: 18 },
  average_order_value: "14160.00",
  series: SERIES,
  pipeline: [
    { status: "placed", label: "Placed", count: 1 },
    { status: "payment_confirmed", label: "Payment confirmed", count: 3 },
    { status: "measurement_review", label: "Measurement review", count: 1 },
    { status: "in_atelier", label: "In atelier", count: 2 },
    { status: "stitching", label: "Stitching", count: 4 },
    { status: "quality_check", label: "Quality check", count: 0 },
    { status: "packed", label: "Packed", count: 2 },
    { status: "shipped", label: "Shipped", count: 5 },
    { status: "return_requested", label: "Return requested", count: 0 },
  ],
  moderation: { reviews_pending: 2, photos_needing_review: 1 },
  low_stock: [
    { sku: "VG-EM-S", product_name: "Velvet Gharara - Emerald", product_slug: "velvet-gharara-emerald", size: "S", colour: "Emerald", stock_quantity: 0 },
    { sku: "KL-IV-M", product_name: "Karachi Lawn Chikankari - Ivory", product_slug: "karachi-lawn-ivory", size: "M", colour: "Ivory", stock_quantity: 1 },
  ],
  recent_orders: RECENT_ORDERS,
};

/** The day the atelier opened: nothing sold, nothing waiting. */
export const QUIET_SUMMARY: DashboardSummary = {
  ...SUMMARY,
  revenue: { month_to_date: "0.00", previous_period: "0.00" },
  orders: { month_to_date: 0, previous_period: 0 },
  average_order_value: null,
  series: SERIES.map((day) => ({ ...day, revenue: "0.00", orders: 0 })),
  pipeline: SUMMARY.pipeline.map((stage) => ({ ...stage, count: 0 })),
  moderation: { reviews_pending: 0, photos_needing_review: 0 },
  low_stock: [],
  recent_orders: [],
};

/** A paid bespoke order, as the back office sees it. */
export const BACK_OFFICE_ORDER: OrderDetail = {
  order_number: "FER-260412",
  status: "payment_confirmed",
  currency: "INR",
  supply_type: "intra_state",
  shipping_address: {
    recipient_name: "Ayesha Khan",
    phone: "+919820012345",
    line1: "402 Imperial Heights",
    city: "Mumbai",
    state_code: "MH",
    postal_code: "400001",
    country_code: "IN",
  },
  subtotal: "12000.00",
  shipping_charge: "0.00",
  tax_total: "2160.00",
  grand_total: "14160.00",
  lines: [
    {
      id: "line-1",
      sku: "KL-IV-M",
      product_name: "Karachi Lawn Chikankari - Ivory",
      variant_label: "M / Ivory",
      quantity: 1,
      unit_price: "12000.00",
      gross: "12000.00",
      is_bespoke: true,
    },
  ],
  tax_snapshot: { cgst_total: "1080.00", sgst_total: "1080.00", igst_total: "0.00" },
  placed_at: "2026-11-20T08:50:00Z",
  customer_name: "Ayesha Khan",
  contact_email: "ayesha@example.com",
  customer_notes: "Please keep the sleeves full length; Nikah on 12 December.",
  events: [
    { id: 2, from_status: "placed", to_status: "payment_confirmed", actor_name: "Razorpay", reason: "", created_at: "2026-11-20T08:52:00Z" },
    { id: 1, from_status: "draft", to_status: "placed", actor_name: "Ayesha Khan", reason: "", created_at: "2026-11-20T08:50:00Z" },
  ],
  next_statuses: ["cancelled", "in_atelier", "measurement_review", "packed"],
};
