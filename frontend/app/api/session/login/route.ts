import { type NextRequest, NextResponse } from "next/server";

import { backendOrigin, upstreamHeaders, writeSessionCookies } from "@/lib/session";

/** Customer-facing wording for a refused sign-in. */
function failureDetail(status: number, upstreamDetail: unknown): string {
  if (status === 401) return "That email and password don't match an account.";
  if (status === 429) {
    // Django's per-account lockout explains itself; the per-IP throttle does not.
    return typeof upstreamDetail === "string" && upstreamDetail.includes("this account")
      ? upstreamDetail
      : "Too many attempts. Please wait a minute and try again.";
  }
  return typeof upstreamDetail === "string" ? upstreamDetail : "Sign-in failed. Please try again.";
}

/** POST /api/session/login - exchange credentials for session cookies. */
export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => null)) as {
    email?: unknown;
    password?: unknown;
    remember?: unknown;
  } | null;
  if (typeof body?.email !== "string" || typeof body?.password !== "string") {
    return NextResponse.json({ detail: "Enter your email and password." }, { status: 400 });
  }

  const upstream = await fetch(`${backendOrigin()}/api/v1/auth/token/`, {
    method: "POST",
    headers: upstreamHeaders(request.headers),
    body: JSON.stringify({ email: body.email, password: body.password }),
    cache: "no-store",
  });
  const data = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;

  if (!upstream.ok) {
    const detail = failureDetail(upstream.status, data.detail);
    return NextResponse.json({ detail }, { status: upstream.status });
  }

  const response = NextResponse.json({ user: data.user });
  writeSessionCookies(
    response,
    { access: String(data.access), refresh: String(data.refresh) },
    // Remembered unless the visitor explicitly un-ticked "Remember me".
    { persistent: body.remember !== false },
  );
  return response;
}
