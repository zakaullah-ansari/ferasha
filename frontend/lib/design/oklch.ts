/**
 * OKLCH → sRGB conversion for the shadcn preset colours.
 *
 * The preset authors its tokens in OKLCH (`app/globals.css`), while the WCAG
 * maths in `tokens.ts` works on sRGB hex. Converting here lets the preset go
 * through the *same* contrast functions as the Ferasha palette rather than a
 * second, subtly different implementation: see `tests/preset-contrast.test.ts`.
 *
 * Out-of-gamut colours are clipped per channel, which is what browsers do when
 * painting to an sRGB display.
 */

/** A parsed `oklch()` value. `l` is 0–1, `h` in degrees, `alpha` 0–1. */
export interface Oklch {
  l: number;
  c: number;
  h: number;
  alpha: number;
}

const OKLCH_PATTERN =
  /^oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?\s*(?:\/\s*([\d.]+)(%?)\s*)?\)$/;

/** Parse a CSS `oklch(L C H [/ A])` string, as written in `globals.css`. */
export function parseOklch(value: string): Oklch {
  const match = value.trim().match(OKLCH_PATTERN);
  if (!match) {
    throw new Error(`Expected an oklch() colour, received "${value}".`);
  }
  const [, l, lPercent, c, h, alpha, alphaPercent] = match;
  return {
    l: lPercent ? Number(l) / 100 : Number(l),
    c: Number(c),
    h: Number(h),
    alpha: alpha === undefined ? 1 : alphaPercent ? Number(alpha) / 100 : Number(alpha),
  };
}

function gammaEncode(linear: number): number {
  const clipped = Math.min(1, Math.max(0, linear));
  return clipped <= 0.0031308
    ? 12.92 * clipped
    : 1.055 * Math.pow(clipped, 1 / 2.4) - 0.055;
}

/** OKLCH → gamma-encoded sRGB channels, each 0–1 (Björn Ottosson's matrices). */
export function oklchToSrgb({ l, c, h }: Oklch): [number, number, number] {
  const hue = (h * Math.PI) / 180;
  const a = c * Math.cos(hue);
  const b = c * Math.sin(hue);

  const lms = [
    l + 0.3963377774 * a + 0.2158037573 * b,
    l - 0.1055613458 * a - 0.0638541728 * b,
    l - 0.0894841775 * a - 1.291485548 * b,
  ].map((v) => v ** 3) as [number, number, number];
  const [L, M, S] = lms;

  return [
    gammaEncode(4.0767416621 * L - 3.3077115913 * M + 0.2309699292 * S),
    gammaEncode(-1.2684380046 * L + 2.6097574011 * M - 0.3413193965 * S),
    gammaEncode(-0.0041960863 * L - 0.7034186147 * M + 1.707614701 * S),
  ];
}

function toHex(channels: [number, number, number]): string {
  return `#${channels
    .map((v) => Math.round(v * 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

function hexChannels(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(value)) {
    throw new Error(`Expected a 6-digit hex colour, received "${hex}".`);
  }
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255) as [
    number,
    number,
    number,
  ];
}

function mix(
  fg: [number, number, number],
  alpha: number,
  backdrop: string,
): string {
  const bg = hexChannels(backdrop);
  return toHex(
    fg.map((v, i) => v * alpha + bg[i]! * (1 - alpha)) as [number, number, number],
  );
}

/**
 * Paint `hex` at `alpha` over `backdrop`, in gamma-encoded sRGB as browsers
 * blend. This is what a utility like `bg-primary/5` resolves to on screen.
 */
export function blend(hex: string, alpha: number, backdrop: string): string {
  return mix(hexChannels(hex), alpha, backdrop);
}

/**
 * The sRGB hex a browser paints for an `oklch()` value.
 *
 * Translucent colours (the preset's dark-mode borders are `oklch(1 0 0 / 10%)`)
 * are composited over `backdrop`.
 */
export function oklchToHex(value: string, backdrop = "#ffffff"): string {
  const colour = parseOklch(value);
  const fg = oklchToSrgb(colour);
  return colour.alpha >= 1 ? toHex(fg) : mix(fg, colour.alpha, backdrop);
}
