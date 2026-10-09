/**
 * Length conversion for the FitDrawer.
 *
 * This looks trivial and is not. A tailor cuts cloth from these numbers: an
 * error here is a garment that does not fit, already paid for.
 *
 * **Design note, learned the hard way.** An earlier version of this module
 * assumed a canonical unit (centimetres) and exposed `parseFromDisplay` /
 * `formatForDisplay` built around that assumption. The fit contract is
 * canonical *inches*, so every measurement was silently multiplied by 2.54
 * before submission. Both modules were individually correct and the
 * combination was catastrophic.
 *
 * The API below therefore has **no implicit canonical unit**. Every
 * conversion names both its source and its target, so the compiler sees a
 * mismatch that a reviewer would not.
 */

export type Unit = "cm" | "inch";

/** Exact, by international agreement since 1959. */
export const CM_PER_INCH = 2.54;

/** Display precision per unit. Tailors work to roughly an eighth of an inch. */
const DECIMALS: Record<Unit, number> = { inch: 2, cm: 1 };

function round(value: number, decimals: number): number {
  // Number.EPSILON lifts values sitting a hair below the .5 boundary in
  // binary floating point: (1.005).toFixed(2) is "1.00" without it.
  const factor = 10 ** decimals;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function assertFinite(value: number, label: string): void {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new TypeError(`Expected a finite number for ${label}, received ${value}.`);
  }
}

/**
 * Convert between units. Both ends are named explicitly — there is no
 * "default" unit to get wrong.
 */
export function convert(value: number, from: Unit, to: Unit): number {
  assertFinite(value, "value");
  if (from === to) return value;
  return from === "inch" ? value * CM_PER_INCH : value / CM_PER_INCH;
}

export function cmToInch(cm: number): number {
  return convert(cm, "cm", "inch");
}

export function inchToCm(inch: number): number {
  return convert(inch, "inch", "cm");
}

/**
 * Convert a stored value into the unit shown on screen, rounded for display.
 * Rounding happens here and nowhere else.
 */
export function toDisplay(value: number, stored: Unit, shown: Unit): number {
  return round(convert(value, stored, shown), DECIMALS[shown]);
}

/**
 * Convert a value the user typed into the unit used for storage.
 * Deliberately unrounded — the stored value keeps full precision.
 */
export function fromDisplay(value: number, shown: Unit, stored: Unit): number {
  return convert(value, shown, stored);
}

/** Render a measurement with its unit, for screen readers and summaries. */
export function describeMeasurement(
  value: number,
  stored: Unit,
  shown: Unit,
): string {
  const display = toDisplay(value, stored, shown);
  return shown === "cm" ? `${display} cm` : `${display} in`;
}

/** Convert a whole set of stored measurements for display. */
export function convertRecord<K extends string>(
  measurements: Readonly<Record<K, number>>,
  stored: Unit,
  shown: Unit,
): Record<K, number> {
  const output = {} as Record<K, number>;
  for (const key of Object.keys(measurements) as K[]) {
    output[key] = toDisplay(measurements[key], stored, shown);
  }
  return output;
}
