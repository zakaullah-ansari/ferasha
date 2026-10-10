/**
 * Contrast is a hard constraint, so it is a test rather than a guideline.
 *
 * The failure this suite prevents is specific and extremely easy to commit:
 * brand gold is a beautiful colour and a designer will reach for it on a
 * paragraph. At 2.38:1 on ivory that paragraph is unreadable for a large
 * number of users, and it will pass code review because it *looks* fine on a
 * calibrated laptop in a bright room.
 */

import { describe, expect, it } from "vitest";

import {
  BODY_TEXT_ON_IVORY,
  BRAND,
  WCAG,
  contrastRatio,
  gold,
  ink,
  luminance,
  passesBodyText,
  passesLargeText,
  semantic,
  surface,
} from "@/lib/design/tokens";

describe("contrast maths", () => {
  it("matches the WCAG reference values at the extremes", () => {
    // Black on white is the canonical 21:1.
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(contrastRatio("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
  });

  it("is order independent", () => {
    expect(contrastRatio(BRAND.gold, BRAND.ivory)).toBeCloseTo(
      contrastRatio(BRAND.ivory, BRAND.gold),
      10,
    );
  });

  it("rejects malformed colours instead of silently returning a number", () => {
    expect(() => luminance("#fff")).toThrow(/6-digit hex/);
    expect(() => luminance("rebeccapurple")).toThrow(/6-digit hex/);
  });
});

describe("the brand palette as specified", () => {
  it("confirms brand gold fails AA on ivory", () => {
    // This is the whole reason the gold ramp has a 700 step. If this
    // assertion ever starts failing, brand gold has been altered and every
    // decorative-only rule below needs revisiting.
    const ratio = contrastRatio(BRAND.gold, BRAND.ivory);
    expect(ratio).toBeLessThan(WCAG.AA_BODY);
    expect(ratio).toBeCloseTo(2.38, 2);
  });

  it("confirms obsidian on ivory is comfortably legible", () => {
    expect(contrastRatio(BRAND.obsidian, BRAND.ivory)).toBeGreaterThan(15);
  });
});

describe("every token approved for body text actually passes AA", () => {
  it.each(BODY_TEXT_ON_IVORY.map((c) => [c] as const))(
    "%s carries body text on ivory",
    (colour) => {
      expect(passesBodyText(colour, surface.page)).toBe(true);
    },
  );

  it("does not list brand gold as a body-text colour", () => {
    expect(BODY_TEXT_ON_IVORY).not.toContain(BRAND.gold);
    expect(BODY_TEXT_ON_IVORY as readonly string[]).not.toContain(gold[500]);
  });
});

describe("gold ramp", () => {
  it("is ordered light to dark", () => {
    const steps = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const;
    const luminances = steps.map((s) => luminance(gold[s]));
    for (let i = 1; i < luminances.length; i += 1) {
      expect(luminances[i]!).toBeLessThan(luminances[i - 1]!);
    }
  });

  it("provides a text-safe gold, because the brand gold is not", () => {
    expect(passesBodyText(gold[700], surface.page)).toBe(true);
  });

  it("keeps 500 and lighter out of text use", () => {
    for (const step of [50, 100, 200, 300, 400, 500] as const) {
      expect(passesBodyText(gold[step], surface.page)).toBe(false);
    }
  });

  it("can carry obsidian text on a gold fill, for CTA buttons", () => {
    // The gold button only works if the label on it is dark.
    expect(passesBodyText(BRAND.obsidian, gold[500])).toBe(true);
    expect(passesBodyText(BRAND.ivory, gold[500])).toBe(false);
  });
});

describe("ink ramp", () => {
  it("runs from the page ground to the ink, giving distinguishable steps", () => {
    const steps = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const;
    const luminances = steps.map((s) => luminance(ink[s]));
    for (let i = 1; i < luminances.length; i += 1) {
      expect(luminances[i]!).toBeLessThan(luminances[i - 1]!);
      // Each step must be perceptibly different from the last. A ramp whose
      // top end is eight shades of the same near-black is not a ramp.
      expect(luminances[i - 1]! - luminances[i]!).toBeGreaterThan(0.002);
    }
  });

  it("documents the lightest step usable for body copy", () => {
    expect(passesBodyText(ink[600], surface.page)).toBe(true);
    expect(passesBodyText(ink[500], surface.page)).toBe(false);
    // ink-500 is still fine for large text.
    expect(passesLargeText(ink[500], surface.page)).toBe(true);
  });

  it("supplies a border colour that clears the 3:1 non-text threshold", () => {
    // Input borders and focus rings are non-text UI and still need 3:1.
    expect(contrastRatio(ink[500], surface.page)).toBeGreaterThanOrEqual(
      WCAG.AA_NON_TEXT,
    );
  });
});

describe("semantic colours", () => {
  it.each(Object.entries(semantic))("%s is legible on the page ground", (_n, hex) => {
    expect(passesBodyText(hex, surface.page)).toBe(true);
  });

  it.each(Object.entries(semantic))("%s is legible on a raised surface", (_n, hex) => {
    expect(passesBodyText(hex, surface.raised)).toBe(true);
  });

  it("keeps danger distinguishable from warning by luminance, not just hue", () => {
    // Red/amber confusion is the most common colour-vision collision. If the
    // two differ only in hue, a deuteranopic user sees one colour.
    const delta = Math.abs(luminance(semantic.danger) - luminance(semantic.warning));
    expect(delta).toBeGreaterThan(0.01);
  });
});

describe("inverse surface", () => {
  it("carries ivory text, for the footer", () => {
    expect(passesBodyText(BRAND.ivory, surface.inverse)).toBe(true);
  });

  it("is the one place brand gold may carry text", () => {
    // 7.08:1 — on obsidian, gold is genuinely legible. This is why the footer
    // can use it and the page body cannot.
    expect(passesBodyText(BRAND.gold, surface.inverse)).toBe(true);
  });
});
