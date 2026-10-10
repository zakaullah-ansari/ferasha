/**
 * Ferasha design tokens — the single source of truth for colour.
 *
 * Tailwind reads these via `app/globals.css` (`@theme`). They are exported as
 * TypeScript so the contrast rules can be *tested* rather than asserted in a
 * comment: see `tests/contrast.test.ts`.
 *
 * The brand supplies three hexes. Three hexes are not a design system — hover,
 * active, disabled, borders and focus rings all need tonal steps, and every one
 * of them needs its contrast verified.
 */

/** Brand constants, exactly as specified. These three are not negotiable. */
export const BRAND = {
  gold: "#c5a059",
  obsidian: "#1a1a1a",
  ivory: "#fdfbf7",
} as const;

/**
 * Gold ramp.
 *
 * Brand gold sits at 500 and measures **2.38:1** on ivory — it fails WCAG AA
 * (4.5:1) for body text and even fails the 3:1 large-text threshold. It is
 * therefore a *decorative* colour: borders, dividers, large display type,
 * and fills behind dark text.
 *
 * `gold-700` (4.99:1) exists so that gold-coloured *text* is possible at all.
 * Any gold word on an ivory ground must use 700 or darker.
 */
export const gold = {
  50: "#faf7f2",
  100: "#f6f0e4",
  200: "#ece1ca",
  300: "#e1cea9",
  400: "#d3b781",
  500: BRAND.gold,
  600: "#a28349",
  700: "#826a3b",
  800: "#5f4d2b",
  900: "#3b301b",
} as const;

/**
 * Neutral ramp, interpolated ivory → obsidian.
 *
 * Deliberately *not* a ramp centred on obsidian: obsidian is already near-black,
 * so steps above it are visually identical and useless. Running the ramp from
 * the page ground to the ink gives ten distinguishable steps that are actually
 * usable for borders, muted text and disabled states.
 *
 * `ink-500` (4.22:1) is the lightest step permitted for large text; `ink-600`
 * is the lightest permitted for body copy.
 */
export const ink = {
  50: "#f6f4f0",
  100: "#edebe8",
  200: "#dddcd8",
  300: "#c2c1be",
  400: "#9e9d9a",
  500: "#797977",
  600: "#5e5e5c",
  700: "#474746",
  800: "#313130",
  900: BRAND.obsidian,
} as const;

/**
 * Semantic colours. A luxury palette still has to render an error legibly;
 * these are desaturated to sit beside the brand rather than shout over it.
 * Each is chosen to clear 4.5:1 on ivory so it can carry text.
 */
export const semantic = {
  success: "#2f6b4f",
  warning: "#8a5a1f",
  danger: "#9b2c2c",
  info: "#2c5282",
} as const;

/** Surfaces. */
export const surface = {
  page: BRAND.ivory,
  raised: "#ffffff",
  sunken: ink[50],
  inverse: BRAND.obsidian,
} as const;

/**
 * Minimum contrast ratios from WCAG 2.2.
 * `large` applies at >=24px, or >=18.66px when bold.
 */
export const WCAG = {
  AA_BODY: 4.5,
  AA_LARGE: 3.0,
  /** Non-text UI: focus rings, input borders, icon-only controls. */
  AA_NON_TEXT: 3.0,
} as const;

/* -------------------------------------------------------------------------- */
/* Contrast maths — WCAG 2.x relative luminance.                              */
/* -------------------------------------------------------------------------- */

function channels(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(value)) {
    throw new Error(`Expected a 6-digit hex colour, received "${hex}".`);
  }
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16)) as [
    number,
    number,
    number,
  ];
}

function linearise(channel: number): number {
  const c = channel / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** WCAG relative luminance. */
export function luminance(hex: string): number {
  const [r, g, b] = channels(hex).map(linearise) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio, always >= 1, order-independent. */
export function contrastRatio(a: string, b: string): number {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [
    number,
    number,
  ];
  return (lighter + 0.05) / (darker + 0.05);
}

/** Does this pairing carry body text? */
export function passesBodyText(fg: string, bg: string): boolean {
  return contrastRatio(fg, bg) >= WCAG.AA_BODY;
}

/** Does this pairing carry large display text or a non-text UI boundary? */
export function passesLargeText(fg: string, bg: string): boolean {
  return contrastRatio(fg, bg) >= WCAG.AA_LARGE;
}

/**
 * Colours approved for body copy on the ivory page ground.
 *
 * Exported so components can be constrained at the type level rather than
 * relying on a reviewer noticing `text-gold-500` on a paragraph.
 */
export const BODY_TEXT_ON_IVORY = [
  ink[600],
  ink[700],
  ink[800],
  ink[900],
  gold[700],
  gold[800],
  gold[900],
  semantic.success,
  semantic.warning,
  semantic.danger,
  semantic.info,
] as const;
