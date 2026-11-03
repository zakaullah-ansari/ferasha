/**
 * The admin (django-unfold) derives its palette from two storefront colours
 * copied into backend-core/config/admin_ui.py. globals.css is the single
 * source of truth; this fails CI the moment the copy drifts from it.
 *
 * Reads the backend file across the repo, like fit-contract.test.ts: runs in
 * any full checkout (CI), not inside the frontend-only container.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");
const adminUi = readFileSync(join(process.cwd(), "../backend-core/config/admin_ui.py"), "utf8");

function storefront(token: string): string {
  const root = css.match(/^:root\s*\{([^}]*)\}/m)?.[1] ?? "";
  const value = root.match(new RegExp(`--${token}:\s*([^;]+);`))?.[1];
  if (!value) throw new Error(`--${token} not found in :root`);
  return value.trim();
}

function admin(constant: string): string {
  const value = adminUi.match(new RegExp(`^${constant} = "([^"]+)"`, "m"))?.[1];
  if (!value) throw new Error(`${constant} not found in admin_ui.py`);
  return value;
}

describe("admin colours follow the storefront", () => {
  it("primary", () => {
    expect(admin("STOREFRONT_PRIMARY")).toBe(storefront("primary"));
  });

  it("ink the neutral greys are tinted from", () => {
    expect(admin("STOREFRONT_FOREGROUND")).toBe(storefront("foreground"));
  });
});
