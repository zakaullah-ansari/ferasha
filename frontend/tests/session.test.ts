/**
 * The security decisions behind the cookie session: when to refresh, which
 * requests count as same-origin (CSRF), and where sign-in may send you back to
 * (open redirect).
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

import { safeNextPath } from "@/lib/api/server";
import { isExpiring, isSafeMethod, isSameOrigin, tokenExpiry } from "@/lib/session";

/** An unsigned JWT-shaped string; only the payload matters here. */
function jwt(payload: object): string {
  const encode = (value: object) =>
    btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${encode({ alg: "HS256" })}.${encode(payload)}.signature`;
}

describe("token expiry", () => {
  const now = Date.UTC(2026, 10, 2, 12, 0, 0);
  const inSeconds = (s: number) => Math.floor(now / 1000) + s;

  it("reads exp from the payload", () => {
    expect(tokenExpiry(jwt({ exp: 1234 }))).toBe(1234);
  });

  it("is fresh well before expiry", () => {
    expect(isExpiring(jwt({ exp: inSeconds(600) }), now)).toBe(false);
  });

  it("refreshes inside the skew window, before Django would reject it", () => {
    expect(isExpiring(jwt({ exp: inSeconds(10) }), now)).toBe(true);
  });

  it("treats an unreadable token as expired rather than trusting it", () => {
    expect(isExpiring("not-a-jwt", now)).toBe(true);
    expect(isExpiring(jwt({ sub: "no-exp" }), now)).toBe(true);
  });
});

describe("same-origin check (CSRF)", () => {
  const headers = (init: Record<string, string>) => new Headers(init);

  it("accepts our own origin", () => {
    expect(isSameOrigin(headers({ origin: "http://localhost:3000", host: "localhost:3000" }))).toBe(true);
  });

  it("honours the proxy's forwarded host", () => {
    expect(
      isSameOrigin(
        headers({ origin: "https://www.ferasha.com", host: "frontend:3000", "x-forwarded-host": "www.ferasha.com" }),
      ),
    ).toBe(true);
  });

  it.each([
    ["another site", { origin: "https://evil.example", host: "localhost:3000" }],
    ["a look-alike subdomain", { origin: "http://localhost:3000.evil.example", host: "localhost:3000" }],
    ["no Origin at all", { host: "localhost:3000" }],
    ["a malformed Origin", { origin: "null", host: "localhost:3000" }],
  ])("refuses %s", (_label, init) => {
    expect(isSameOrigin(headers(init))).toBe(false);
  });

  it("only guards state-changing methods", () => {
    expect(isSafeMethod("GET")).toBe(true);
    expect(isSafeMethod("post")).toBe(false);
    expect(isSafeMethod("DELETE")).toBe(false);
  });
});

describe("return path after sign-in", () => {
  it.each([
    ["/checkout", "/checkout"],
    ["/orders/FER-ABC?placed=1", "/orders/FER-ABC?placed=1"],
    [undefined, "/"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["checkout", "/"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});
