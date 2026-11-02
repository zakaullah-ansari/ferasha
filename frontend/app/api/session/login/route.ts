import { type NextRequest, NextResponse } from "next/server";

import { backendOrigin, upstreamHeaders, writeSessionCookies } from "@/lib/session";

/** POST /api/session/login - exchange credentials for session cookies. */
export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => null)) as {
    email?: unknown;
    password?: unknown;
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
    const detail =
      upstream.status === 401
        ? "That email and password don't match an account."
        : upstream.status === 429
          ? "Too many attempts. Please wait a minute and try again."
          : typeof data.detail === "string"
            ? data.detail
            : "Sign-in failed. Please try again.";
    return NextResponse.json({ detail }, { status: upstream.status });
  }

  const response = NextResponse.json({ user: data.user });
  writeSessionCookies(response, { access: String(data.access), refresh: String(data.refresh) });
  return response;
}
