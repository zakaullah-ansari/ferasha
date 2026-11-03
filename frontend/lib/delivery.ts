/**
 * Delivery terms as shown to shoppers.
 *
 * Display copy only: checkout prices delivery on the server
 * (backend-core settings FERASHA_SHIPPING_HOME_STATE / _DOMESTIC), and the
 * quote is what the customer pays. Keep these in step with those settings.
 */
export const DELIVERY = {
  summary: "Free delivery within Maharashtra · ₹150 elsewhere in India",
  international: "International delivery is not available yet.",
} as const;
