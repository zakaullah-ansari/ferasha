/**
 * The owner dashboard's door, checked on the server before anything renders.
 *
 * Not signed in: to sign-in, then back. Signed in without back-office rights:
 * a plain 404, so the dashboard's existence is not advertised. The API checks
 * again on every request; this only decides what the page shows.
 */

import { notFound } from "next/navigation";

import { getSignedIn, requireSession } from "@/lib/api/server";
import type { SessionUser } from "@/lib/api/types";

export async function requireBackOffice(): Promise<SessionUser> {
  const user = await requireSession("/dashboard");
  if (!user.is_back_office) notFound();
  return user;
}

/** A back-office read; an expired session goes back through sign-in to the dashboard. */
export function getBackOffice<T>(path: string): Promise<T> {
  return getSignedIn<T>(path, "/dashboard");
}
