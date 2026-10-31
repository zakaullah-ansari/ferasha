/**
 * The CSS theme and the TypeScript tokens must agree.
 *
 * `tokens.ts` is contrast-tested; `globals.css` is what the browser actually
 * paints. If someone tweaks a hex in the CSS — the far more likely place to
 * fiddle with colour — the tested guarantee silently stops describing the
 * shipped product. This test closes that gap by parsing the real CSS file.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { gold, ink, semantic, surface } from "@/lib/design/tokens";

const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

function cssVar(name: string): string | undefined {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})\\s*;`));
  return match?.[1]?.toLowerCase();
}

describe("globals.css mirrors lib/design/tokens.ts", () => {
  it.each(Object.entries(gold))("gold-%s matches", (step, hex) => {
    expect(cssVar(`color-gold-${step}`)).toBe(hex.toLowerCase());
  });

  it.each(Object.entries(ink))("ink-%s matches", (step, hex) => {
    expect(cssVar(`color-ink-${step}`)).toBe(hex.toLowerCase());
  });

  it.each(Object.entries(semantic))("semantic %s matches", (name, hex) => {
    expect(cssVar(`color-${name}`)).toBe(hex.toLowerCase());
  });

  it("page ground matches", () => {
    expect(cssVar("color-ivory")).toBe(surface.page.toLowerCase());
  });

  it("raised surface matches", () => {
    expect(cssVar("color-surface-raised")).toBe(surface.raised.toLowerCase());
  });
});

describe("accessibility rules that live in CSS", () => {
  it("honours prefers-reduced-motion globally", () => {
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });

  it("defines a visible focus ring rather than removing outlines", () => {
    expect(css).toMatch(/:focus-visible\s*\{[^}]*outline:/);
    // `outline: none` without a replacement is the regression to catch.
    expect(css).not.toMatch(/:focus(-visible)?\s*\{[^}]*outline:\s*(none|0)\s*;/);
  });

  it("leaves .sr-only to Tailwind, so focus:not-sr-only can reveal the skip link", () => {
    // A custom .sr-only using the legacy `clip` property survives
    // not-sr-only, which only resets clip-path: the skip link took focus but
    // stayed clipped to nothing.
    expect(css).not.toMatch(/\.sr-only\s*\{/);
  });
});

describe("typography survives the shadcn preset", () => {
  // `shadcn apply` rewrites font variables; these keep Ferasha's faces in place.
  it("keeps the UI face on Inter", () => {
    expect(css).toMatch(/--font-sans:\s*var\(--font-ui-sans\)/);
  });

  it("gives shadcn titles the display serif, like every other heading", () => {
    expect(css).toMatch(/--font-heading:\s*var\(--font-display\)/);
  });
});
