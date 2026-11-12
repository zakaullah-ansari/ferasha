/** The storefront's security headers: always-on basics, production-only framing and HSTS. */

import { describe, expect, it } from "vitest";

import nextConfig from "@/next.config";
import { securityHeaders } from "@/lib/security-headers";

const asMap = (production: boolean) =>
  Object.fromEntries(securityHeaders({ production }).map((header) => [header.key, header.value]));

describe("security headers", () => {
  it("production refuses framing and pins HTTPS", () => {
    const headers = asMap(true);
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["X-Frame-Options"]).toBe("DENY");
    expect(headers["Strict-Transport-Security"]).toMatch(/max-age=31536000/);
  });

  it("development keeps the basics but allows previews and plain http", () => {
    const headers = asMap(false);
    expect(headers["Content-Security-Policy"]).not.toContain("frame-ancestors");
    expect(headers["X-Frame-Options"]).toBeUndefined();
    expect(headers["Strict-Transport-Security"]).toBeUndefined();
  });

  it.each(["X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Opener-Policy"])(
    "%s is always sent",
    (key) => {
      expect(asMap(false)[key]).toBeTruthy();
      expect(asMap(true)[key]).toBeTruthy();
    },
  );

  it("applies to every path", async () => {
    const rules = await nextConfig.headers!();
    expect(rules).toHaveLength(1);
    expect(rules[0]?.source).toBe("/:path*");
  });
});
