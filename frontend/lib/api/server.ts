/**
 * Signed-in reads for Server Components.
 *
 * These run on the storefront server, so they call Django directly with the
 * access token from the request's cookies. By the time a page renders, the
 * middleware has already refreshed an expiring token and forwarded the new
 * cookie, so the value read here is current.
 */

import { cookies } from "next/headers";

import { redirect } from "next/navigation";

import { ACCESS_COOKIE, REFRESH_COOKIE, backendOrigin } from "@/lib/session";

import { ApiError } from "./client";
import type { SessionUser, SocialProvider } from "./types";

/** True when the visitor holds a session (it may still need a refresh). */
export async function hasSession(): Promise<boolean> {
  const jar = await cookies();
  return Boolean(jar.get(ACCESS_COOKIE)?.value || jar.get(REFRESH_COOKIE)?.value);
}

export async function getAuthed<T>(path: string): Promise<T> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  const response = await fetch(`${backendOrigin()}${path}`, {
    headers: {
      Accept: "application/json",
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(response.status, path, `Request to ${path} failed with ${response.status}.`);
  }
  return (await response.json()) as T;
}

/**
 * Outside sign-ins Django has keys for; [] when none are, or Django is away
 * (the email form still works). Cached briefly: it changes only on deploy.
 */
export async function getSocialProviders(): Promise<readonly SocialProvider[]> {
  try {
    const response = await fetch(`${backendOrigin()}/api/v1/auth/social/providers/`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 300 },
    });
    if (!response.ok) return [];
    const data = (await response.json()) as { providers?: SocialProvider[] };
    return Array.isArray(data.providers) ? data.providers : [];
  } catch {
    return [];
  }
}

const signIn = (next: string) => `/account/sign-in?next=${encodeURIComponent(next)}`;

/** The signed-in visitor, or a trip through sign-in that comes back to `next`. */
export async function requireSession(next: string): Promise<SessionUser> {
  if (!(await hasSession())) redirect(signIn(next));
  return getSignedIn<SessionUser>("/api/v1/auth/me/", next);
}

/** A signed-in read. A session that ran out mid-visit goes back through sign-in; other errors are the caller's. */
export async function getSignedIn<T>(path: string, next: string): Promise<T> {
  try {
    return await getAuthed<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect(signIn(next));
    throw error;
  }
}

/**
 * A same-site path to return to after sign-in, or "/" for anything else.
 *
 * Parsed, not prefix-matched: browsers strip tabs and newlines from URLs, so
 * "/\t/evil.com" (a literal tab) passes a startsWith("//") check yet goes to
 * //evil.com. Control characters and backslashes are refused outright, then
 * the value must resolve against a placeholder origin without leaving it.
 */
export function safeNextPath(next: string | string[] | undefined): string {
  const value = Array.isArray(next) ? next[0] : next;
  if (!value || !value.startsWith("/") || /[\u0000-\u001f\u007f\\]/.test(value)) return "/";
  const base = "http://same-origin.invalid";
  let url: URL;
  try {
    url = new URL(value, base);
  } catch {
    return "/";
  }
  if (url.origin !== base) return "/";
  // Check the string actually returned, after normalisation: dot segments
  // ("/.//evil.com", "/x/..//evil.com", "/%2e//evil.com") resolve inside the
  // placeholder origin yet normalise to "//evil.com" - protocol-relative.
  const path = `${url.pathname}${url.search}${url.hash}`;
  return path.startsWith("//") ? "/" : path;
}
