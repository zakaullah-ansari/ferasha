/**
 * Sign in with an outside provider (Google today): the storefront's half.
 *
 * Django owns the provider keys and builds the provider URL; the storefront
 * owns the browser. Between leaving for the provider and coming back, the
 * one-time `state`, PKCE verifier and nonce wait in a short-lived httpOnly
 * cookie scoped to the OAuth routes. `state` must come back unchanged, which
 * is what stops another site from completing a sign-in in your browser.
 *
 * Pure functions only (this module reaches the browser via the sign-in
 * buttons); the response helper lives in lib/oauth-server.ts.
 */

import { cookieOptions } from "@/lib/session";

export const OAUTH_COOKIE = "ferasha_oauth";
const OAUTH_COOKIE_PATH = "/api/session/oauth";
/** Long enough to pick an account; short enough that a stale tab cannot reuse it. */
const OAUTH_MAX_AGE_SECONDS = 10 * 60;

/** Provider ids are short lowercase slugs ("google", later "apple"). */
const PROVIDER_ID = /^[a-z][a-z0-9-]{1,31}$/;

export interface PendingOAuth {
  readonly provider: string;
  readonly state: string;
  readonly verifier: string;
  readonly nonce: string;
  /** Already passed through safeNextPath. */
  readonly next: string;
}

export function isProviderId(value: string): boolean {
  return PROVIDER_ID.test(value);
}

/** The link a provider button points at. A plain link: works before hydration. */
export function oauthStartHref(provider: string, next: string): string {
  const base = `/api/session/oauth/${provider}/start`;
  return next === "/" ? base : `${base}?next=${encodeURIComponent(next)}`;
}

export function oauthCookieOptions() {
  return { ...cookieOptions(OAUTH_MAX_AGE_SECONDS), path: OAUTH_COOKIE_PATH };
}

export function serializePending(pending: PendingOAuth): string {
  return JSON.stringify(pending);
}

/** The pending sign-in from the cookie, or null if absent or not ours. */
export function parsePending(raw: string | undefined): PendingOAuth | null {
  if (!raw) return null;
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null) return null;
  const record = value as Record<string, unknown>;
  const keys = ["provider", "state", "verifier", "nonce", "next"] as const;
  if (!keys.every((key) => typeof record[key] === "string" && record[key] !== "")) return null;
  const pending = record as unknown as PendingOAuth;
  // `next` was checked before it was stored; check again, the cookie is input.
  if (!pending.next.startsWith("/") || pending.next.startsWith("//")) return null;
  return pending;
}

/** Fixed reasons the sign-in page knows how to word. Nothing from a URL is ever shown. */
export type OAuthFailure = "oauth-cancelled" | "oauth-failed" | "oauth-conflict" | "oauth-forbidden";

export function failureFor(status: number): OAuthFailure {
  if (status === 409) return "oauth-conflict";
  if (status === 403) return "oauth-forbidden";
  return "oauth-failed";
}

export function failurePath(reason: OAuthFailure, next: string): string {
  const query = new URLSearchParams({ reason });
  if (next !== "/") query.set("next", next);
  return `/account/sign-in?${query.toString()}`;
}
