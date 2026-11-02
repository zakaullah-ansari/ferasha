/**
 * Signed-in reads for Server Components.
 *
 * These run on the storefront server, so they call Django directly with the
 * access token from the request's cookies. By the time a page renders, the
 * middleware has already refreshed an expiring token and forwarded the new
 * cookie, so the value read here is current.
 */

import { cookies } from "next/headers";

import { ACCESS_COOKIE, REFRESH_COOKIE, backendOrigin } from "@/lib/session";

import { ApiError } from "./client";

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
 * A same-site path to return to after sign-in, or "/" for anything else.
 * Rejects absolute and protocol-relative URLs ("//evil.com"), which would turn
 * the sign-in page into an open redirect.
 */
export function safeNextPath(next: string | string[] | undefined): string {
  const value = Array.isArray(next) ? next[0] : next;
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return "/";
  }
  return value;
}
