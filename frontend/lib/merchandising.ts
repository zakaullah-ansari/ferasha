/**
 * Merchandising labels shown on product cards and pages ("-20%", "New").
 * Pure functions so the rules are tested once and every surface agrees.
 */

/** How long a garment counts as a new arrival after it is listed. */
export const NEW_ARRIVAL_DAYS = 30;

const DAY_MS = 86_400_000;

/**
 * Whole-percent saving of `price` against a struck-through `compareAt`, or
 * null when there is no genuine saving to show. Rounds down so the label can
 * never claim more than the customer actually saves.
 */
export function percentOff(price: string, compareAt: string | null): number | null {
  if (!compareAt) return null;
  // Whole paise: in floating point 1 - 13592/16990 is 0.1999..., which would
  // floor an exact 20% saving down to 19%.
  const now = Math.round(Number(price) * 100);
  const was = Math.round(Number(compareAt) * 100);
  if (!Number.isFinite(now) || !Number.isFinite(was) || was <= 0 || now >= was) return null;
  const percent = Math.floor(((was - now) * 100) / was);
  return percent >= 1 ? percent : null;
}

/** True when the garment was listed within the last NEW_ARRIVAL_DAYS. */
export function isNewArrival(createdAt: string | undefined, now: Date = new Date()): boolean {
  if (!createdAt) return false;
  const listed = Date.parse(createdAt);
  if (Number.isNaN(listed)) return false;
  const age = now.getTime() - listed;
  return age >= 0 && age < NEW_ARRIVAL_DAYS * DAY_MS;
}
