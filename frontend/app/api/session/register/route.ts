import { type NextRequest, NextResponse } from "next/server";

import { backendOrigin, upstreamHeaders, writeSessionCookies } from "@/lib/session";

const FIELDS = ["full_name", "email", "phone", "password", "password_confirm", "accept_terms"];

/** POST /api/session/register - create an account and start its session. */
export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
  if (!body) {
    return NextResponse.json({ detail: "Invalid request." }, { status: 400 });
  }
  // Forward only the fields registration accepts; Django validates them.
  const payload = Object.fromEntries(FIELDS.filter((key) => key in body).map((key) => [key, body[key]]));

  const upstream = await fetch(`${backendOrigin()}/api/v1/auth/register/`, {
    method: "POST",
    headers: upstreamHeaders(request.headers),
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;

  if (!upstream.ok) {
    // 400 bodies are DRF field errors written for customers ("Passwords do
    // not match."); anything else gets a generic message.
    return upstream.status === 400
      ? NextResponse.json(data, { status: 400 })
      : NextResponse.json(
          {
            detail:
              upstream.status === 429
                ? "Too many attempts. Please wait a minute and try again."
                : "Registration failed. Please try again.",
          },
          { status: upstream.status },
        );
  }

  const response = NextResponse.json({ user: data.user }, { status: 201 });
  writeSessionCookies(response, { access: String(data.access), refresh: String(data.refresh) });
  return response;
}
