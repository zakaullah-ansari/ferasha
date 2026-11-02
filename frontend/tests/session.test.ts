/**
 * The security decisions behind the cookie session: when to refresh, which
 * requests count as same-origin (CSRF), and where sign-in may send you back to
 * (open redirect).
 */

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

import { safeNextPath } from "@/lib/api/server";
import { isExpiring, isSafeMethod, isSameOrigin, tokenExpiry, trustedClientIp } from "@/lib/session";

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
    // Browsers strip tab/CR/LF from URLs, turning these into //evil.example.
    ["/\t/evil.example", "/"],
    ["/\n/evil.example", "/"],
    ["/\r/evil.example", "/"],
    ["/\\/evil.example", "/"],
    ["/checkout#review", "/checkout#review"],
  ])("%j -> %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});

describe("client IP for Django's throttles", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("never trusts a visitor's own X-Forwarded-For", () => {
    vi.stubEnv("CLIENT_IP_HEADER", "x-real-ip");
    const spoofed = new Headers({ "x-forwarded-for": "6.6.6.6", "x-real-ip": "203.0.113.7" });
    expect(trustedClientIp(spoofed)).toBe("203.0.113.7");
  });

  it("forwards nothing when no trusted edge header is configured", () => {
    vi.stubEnv("CLIENT_IP_HEADER", "");
    expect(trustedClientIp(new Headers({ "x-forwarded-for": "6.6.6.6" }))).toBeNull();
  });

  it("accepts IPv6 from the edge", () => {
    vi.stubEnv("CLIENT_IP_HEADER", "cf-connecting-ip");
    expect(trustedClientIp(new Headers({ "cf-connecting-ip": "2001:db8::1" }))).toBe("2001:db8::1");
  });

  // (A value with a newline cannot even be constructed: Headers refuses it.)
  it.each(["6.6.6.6, 7.7.7.7", "not-an-ip", "1.2.3.4; evil=1", ""])(
    "rejects a malformed value %j",
    (value) => {
      vi.stubEnv("CLIENT_IP_HEADER", "x-real-ip");
      expect(trustedClientIp(new Headers({ "x-real-ip": value }))).toBeNull();
    },
  );
});
