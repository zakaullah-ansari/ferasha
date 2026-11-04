/**
 * The owner dashboard's door, checked on the server before anything renders.
 *
 * Not signed in: to sign-in, then back. Signed in without back-office rights:
 * a plain 404, so the dashboard's existence is not advertised. The API checks
 * again on every request; this only decides what the page shows.
 */

import { notFound, redirect } from "next/navigation";

import { ApiError } from "@/lib/api/client";
import { getAuthed, hasSession } from "@/lib/api/server";
import type { SessionUser } from "@/lib/api/types";

const SIGN_IN = "/account/sign-in?next=/dashboard";

export async function requireBackOffice(): Promise<SessionUser> {
  if (!(await hasSession())) redirect(SIGN_IN);
  let user: SessionUser;
  try {
    user = await getAuthed<SessionUser>("/api/v1/auth/me/");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect(SIGN_IN);
    throw error;
  }
  if (!user.is_back_office) notFound();
  return user;
}

/** A back-office read. A session that ran out mid-visit goes back through sign-in; other errors are the page's to handle. */
export async function getBackOffice<T>(path: string): Promise<T> {
  try {
    return await getAuthed<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect(SIGN_IN);
    throw error;
  }
}
