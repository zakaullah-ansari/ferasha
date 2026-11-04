/**
 * Currency formatting. INR only — the brief specifies a single currency, and
 * a fake currency switcher that does not actually convert is worse than none.
 */
const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/** Accepts the decimal strings DRF emits, so precision is never lost in JS. */
export function formatINR(value: string | number): string {
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(amount)) return "—";
  return INR.format(amount);
}

const INR_COMPACT = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});

/** Indian grouping, for chart axes: ₹14.2K, ₹3.3L, ₹2.5Cr. */
export function formatINRCompact(value: string | number): string {
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  return Number.isFinite(amount) ? INR_COMPACT.format(amount) : "—";
}
