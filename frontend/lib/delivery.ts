/**
 * Delivery terms as shown to shoppers.
 *
 * Display copy only: checkout prices delivery on the server
 * (backend-core settings FERASHA_SHIPPING_HOME_STATE / _DOMESTIC), and the
 * quote is what the customer pays. Keep these in step with those settings.
 */
const HOME = "Free delivery within Maharashtra";
const ELSEWHERE = "₹150 elsewhere in India";

export const DELIVERY = {
  /** The two halves, for places that set them apart (the trust strip). */
  home: HOME,
  elsewhere: ELSEWHERE,
  summary: `${HOME} · ${ELSEWHERE}`,
  international: "International delivery is not available yet.",
} as const;
