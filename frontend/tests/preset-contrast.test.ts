/**
 * The shadcn preset's colour pairs, held to the same WCAG rules as the
 * Ferasha palette in `contrast.test.ts`.
 *
 * Values are parsed from `app/globals.css`, the file the browser actually
 * paints, so re-applying the preset or hand-tuning a token cannot silently drop
 * a pair the storefront renders below AA.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { blend, oklchToHex, parseOklch } from "@/lib/design/oklch";
import { WCAG, contrastRatio, semantic } from "@/lib/design/tokens";

const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

/** Custom properties declared in the top-level `:root { … }` or `.dark { … }` block. */
function declarations(selector: ":root" | ".dark"): Record<string, string> {
  const escaped = selector.replace(".", "\\.");
  const block = css.match(new RegExp(`^${escaped}\\s*\\{([^}]*)\\}`, "m"))?.[1];
  if (!block) throw new Error(`globals.css has no top-level ${selector} block.`);
  return Object.fromEntries(
    [...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(([, name, value]) => [
      name,
      value!.trim(),
    ]),
  );
}

const light = declarations(":root");
const dark = declarations(".dark");

/** The sRGB hex painted for a token; translucent values sit on that mode's background. */
function paint(tokens: Record<string, string>, name: string): string {
  const value = tokens[`--${name}`];
  if (!value) throw new Error(`--${name} is not declared.`);
  return oklchToHex(value, oklchToHex(tokens["--background"]!));
}

describe("text pairs the storefront renders clear AA body text (4.5:1)", () => {
  it.each([
    ["foreground", "background"],
    ["card-foreground", "card"],
    ["popover-foreground", "popover"],
    ["muted-foreground", "background"],
    ["muted-foreground", "muted"],
    ["primary-foreground", "primary"],
    ["primary", "background"],
    ["secondary-foreground", "secondary"],
    ["accent-foreground", "accent"],
    ["destructive", "background"],
  ])("light: %s on %s", (fg, bg) => {
    expect(contrastRatio(paint(light, fg), paint(light, bg))).toBeGreaterThanOrEqual(
      WCAG.AA_BODY,
    );
  });

  // The site footer is scoped with `.dark`.
  it.each([
    ["foreground", "background"],
    ["muted-foreground", "background"],
  ])("dark: %s on %s", (fg, bg) => {
    expect(contrastRatio(paint(dark, fg), paint(dark, bg))).toBeGreaterThanOrEqual(
      WCAG.AA_BODY,
    );
  });
});

describe("tinted and hover states, composited as the browser paints them", () => {
  const ground = paint(light, "background");
  const primary = paint(light, "primary");

  it("button hover: primary-foreground on primary/95", () => {
    // shadcn's usual hover:bg-primary/90 falls to 4.30:1 with this emerald.
    const hover = blend(primary, 0.95, ground);
    expect(contrastRatio(paint(light, "primary-foreground"), hover)).toBeGreaterThanOrEqual(
      WCAG.AA_BODY,
    );
  });

  it("modesty badge and fit notice: primary and muted text on primary/5", () => {
    const tint = blend(primary, 0.05, ground);
    expect(contrastRatio(primary, tint)).toBeGreaterThanOrEqual(WCAG.AA_BODY);
    expect(contrastRatio(paint(light, "muted-foreground"), tint)).toBeGreaterThanOrEqual(
      WCAG.AA_BODY,
    );
  });

  it("advisory pill: Ferasha's warning on warning/8", () => {
    const tint = blend(semantic.warning, 0.08, ground);
    expect(contrastRatio(semantic.warning, tint)).toBeGreaterThanOrEqual(WCAG.AA_BODY);
  });
});

describe("non-text UI clears 3:1", () => {
  const ground = paint(light, "background");

  it("input borders, the only edge of a white field on a white panel", () => {
    expect(contrastRatio(paint(light, "input"), ground)).toBeGreaterThanOrEqual(
      WCAG.AA_NON_TEXT,
    );
  });

  it.each(["background", "muted"])(
    "the focus ring on --%s, solid and as maia's ring-ring/50 halo",
    (surface) => {
      const ring = paint(light, "ring");
      const behind = paint(light, surface);
      expect(contrastRatio(ring, behind)).toBeGreaterThanOrEqual(WCAG.AA_NON_TEXT);
      expect(contrastRatio(blend(ring, 0.5, behind), behind)).toBeGreaterThanOrEqual(
        WCAG.AA_NON_TEXT,
      );
    },
  );

  it("the focus ring inside the .dark footer", () => {
    expect(contrastRatio(paint(dark, "ring"), paint(dark, "background"))).toBeGreaterThanOrEqual(
      WCAG.AA_NON_TEXT,
    );
  });

  it("draws the global focus outline in --ring", () => {
    expect(css).toMatch(/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--ring\)/);
  });
});

describe("maia variants that tint a token with itself", () => {
  it("destructive text on bg-destructive/10 (destructive Button and Badge)", () => {
    const ground = paint(light, "background");
    const destructive = paint(light, "destructive");
    expect(
      contrastRatio(destructive, blend(destructive, 0.1, ground)),
    ).toBeGreaterThanOrEqual(WCAG.AA_BODY);
  });
});

describe("oklch conversion", () => {
  it("matches sRGB at the extremes", () => {
    expect(oklchToHex("oklch(1 0 0)")).toBe("#ffffff");
    expect(oklchToHex("oklch(0 0 0)")).toBe("#000000");
  });

  it("matches Tailwind's published sRGB values, including a clipped out-of-gamut red", () => {
    // emerald-700 and red-600, both also cross-checked against Chrome's canvas.
    expect(oklchToHex("oklch(0.508 0.118 165.612)")).toBe("#007a55");
    expect(oklchToHex("oklch(0.577 0.245 27.325)")).toBe("#e7000b");
  });

  it("composites translucent colours over the backdrop", () => {
    expect(oklchToHex("oklch(1 0 0 / 25%)", "#000000")).toBe("#404040");
    expect(blend("#ffffff", 0.5, "#000000")).toBe("#808080");
  });

  it("rejects malformed colours instead of silently returning a number", () => {
    expect(() => parseOklch("#fff")).toThrow(/oklch\(\) colour/);
    expect(() => parseOklch("oklch(0.5 0.1)")).toThrow(/oklch\(\) colour/);
  });
});
