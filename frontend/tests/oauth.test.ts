/**
 * Sign in with Google, the storefront's half: the pending cookie, and the
 * callback's refusal to finish a sign-in it did not start (login CSRF).
 */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

import { GET as callback } from "@/app/api/session/oauth/[provider]/callback/route";
import { GET as start } from "@/app/api/session/oauth/[provider]/start/route";
import {
  OAUTH_COOKIE,
  type PendingOAuth,
  failureFor,
  failurePath,
  isProviderId,
  oauthStartHref,
  parsePending,
  serializePending,
} from "@/lib/oauth";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";

const PENDING: PendingOAuth = {
  provider: "google",
  state: "state-123",
  verifier: "v".repeat(64),
  nonce: "nonce-456",
  next: "/checkout",
};

const params = (provider = "google") => ({ params: Promise.resolve({ provider }) });

function callbackRequest(query: string, pending: PendingOAuth | null = PENDING) {
  const headers = new Headers();
  if (pending) headers.set("cookie", `${OAUTH_COOKIE}=${encodeURIComponent(serializePending(pending))}`);
  return new NextRequest(`https://shop.example/api/session/oauth/google/callback?${query}`, { headers });
}

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("helpers", () => {
  it("links to the start route, carrying where to return", () => {
    expect(oauthStartHref("google", "/")).toBe("/api/session/oauth/google/start");
    expect(oauthStartHref("google", "/checkout?step=2")).toBe(
      "/api/session/oauth/google/start?next=%2Fcheckout%3Fstep%3D2",
    );
  });

  it("accepts only slug provider ids", () => {
    expect(isProviderId("google")).toBe(true);
    expect(isProviderId("../token")).toBe(false);
    expect(isProviderId("Google")).toBe(false);
  });

  it("round-trips the pending cookie and rejects anything else", () => {
    expect(parsePending(serializePending(PENDING))).toEqual(PENDING);
    expect(parsePending(undefined)).toBeNull();
    expect(parsePending("not json")).toBeNull();
    expect(parsePending(JSON.stringify({ ...PENDING, state: "" }))).toBeNull();
    expect(parsePending(JSON.stringify({ ...PENDING, next: "//evil.example" }))).toBeNull();
    expect(parsePending(JSON.stringify({ ...PENDING, next: "https://evil.example" }))).toBeNull();
  });

  it("maps Django's refusals to fixed reasons", () => {
    expect(failureFor(409)).toBe("oauth-conflict");
    expect(failureFor(403)).toBe("oauth-forbidden");
    expect(failureFor(400)).toBe("oauth-failed");
    expect(failurePath("oauth-failed", "/")).toBe("/account/sign-in?reason=oauth-failed");
  });
});

describe("start", () => {
  it("stores the one-time secrets and goes to the provider", async () => {
    const fetchMock = stubFetch(200, {
      authorization_url: "https://accounts.google.com/o/oauth2/v2/auth?x=1",
      state: "s",
      code_verifier: "v",
      nonce: "n",
    });
    const response = await start(
      new NextRequest("https://shop.example/api/session/oauth/google/start?next=/checkout"),
      params(),
    );
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/api\/v1\/auth\/social\/google\/authorize\/$/);
    expect(response.headers.get("location")).toBe("https://accounts.google.com/o/oauth2/v2/auth?x=1");
    const cookie = response.cookies.get(OAUTH_COOKIE);
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.path).toBe("/api/session/oauth");
    expect(parsePending(cookie?.value)).toEqual({
      provider: "google",
      state: "s",
      verifier: "v",
      nonce: "n",
      next: "/checkout",
    });
  });

  it("never follows a non-https provider URL", async () => {
    stubFetch(200, { authorization_url: "javascript:alert(1)", state: "s", code_verifier: "v", nonce: "n" });
    const response = await start(new NextRequest("https://shop.example/api/session/oauth/google/start"), params());
    expect(response.headers.get("location")).toBe("/account/sign-in?reason=oauth-failed");
  });

  it("refuses an unsafe return path", async () => {
    stubFetch(200, { authorization_url: "https://accounts.google.com/x", state: "s", code_verifier: "v", nonce: "n" });
    const response = await start(
      new NextRequest("https://shop.example/api/session/oauth/google/start?next=//evil.example"),
      params(),
    );
    expect(parsePending(response.cookies.get(OAUTH_COOKIE)?.value)?.next).toBe("/");
  });
});

describe("callback", () => {
  it("signs in and returns to where the visitor was", async () => {
    const fetchMock = stubFetch(200, { access: "a.b.c", refresh: "d.e.f", created: true });
    const response = await callback(callbackRequest("code=abc&state=state-123"), params());

    expect(JSON.parse(fetchMock.mock.calls[0]?.[1].body)).toEqual({
      code: "abc",
      code_verifier: PENDING.verifier,
      nonce: PENDING.nonce,
    });
    expect(response.headers.get("location")).toBe("/checkout");
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe("a.b.c");
    expect(response.cookies.get(REFRESH_COOKIE)?.value).toBe("d.e.f");
    expect(response.cookies.get(OAUTH_COOKIE)?.value).toBe("");
  });

  it.each([
    ["a different state (login CSRF)", "code=abc&state=forged", PENDING],
    ["no pending cookie", "code=abc&state=state-123", null],
    ["no code", "state=state-123", PENDING],
    ["another provider's cookie", "code=abc&state=state-123", { ...PENDING, provider: "apple" }],
  ])("refuses %s without calling Django", async (_label, query, pending) => {
    const fetchMock = stubFetch(200, { access: "a", refresh: "r" });
    const response = await callback(callbackRequest(query, pending), params());
    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("location")).toContain("reason=oauth-failed");
    expect(response.cookies.get(ACCESS_COOKIE)).toBeUndefined();
    expect(response.cookies.get(OAUTH_COOKIE)?.value).toBe("");
  });

  it("treats Cancel at Google as a cancel, not an error", async () => {
    const response = await callback(callbackRequest("error=access_denied&state=state-123"), params());
    expect(response.headers.get("location")).toBe(
      "/account/sign-in?reason=oauth-cancelled&next=%2Fcheckout",
    );
  });

  it("explains an email that belongs to a password account", async () => {
    stubFetch(409, { detail: "An account already uses this email." });
    const response = await callback(callbackRequest("code=abc&state=state-123"), params());
    expect(response.headers.get("location")).toContain("reason=oauth-conflict");
    expect(response.cookies.get(ACCESS_COOKIE)).toBeUndefined();
  });
});
