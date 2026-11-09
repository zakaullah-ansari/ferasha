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

const DAY = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });
const MOMENT = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "Asia/Kolkata",
});

/** "2026-11-05" (a calendar date, no time) -> "5 Nov", the same in every time zone. */
export function formatDay(isoDate: string): string {
  return DAY.format(new Date(`${isoDate}T00:00:00Z`));
}

/** A timestamp as the atelier in Mumbai saw it: "5 Nov, 2:20 pm". */
export function formatMoment(isoDateTime: string | null): string {
  return isoDateTime ? MOMENT.format(new Date(isoDateTime)) : "—";
}

const DATE = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" });

/** A timestamp as a date in Mumbai: "5 Nov 2026". */
export function formatDate(isoDateTime: string): string {
  return DATE.format(new Date(isoDateTime));
}
