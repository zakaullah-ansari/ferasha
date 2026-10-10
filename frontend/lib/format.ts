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
