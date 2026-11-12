import { type NextRequest, NextResponse } from "next/server";

import { ACCESS_COOKIE, backendOrigin, clearSessionCookies, upstreamHeaders } from "@/lib/session";

const PRIVATE = { "Cache-Control": "private, no-store" };

/**
 * GET /api/session/me - the signed-in customer, or `{ user: null }`.
 *
 * Being a guest is an answer, not an error. Without a session cookie this
 * replies at once, so the header's check on every page view costs guests
 * (most visitors) no call to Django and no 401 in the browser console. By
 * the time this runs the middleware has refreshed an expiring token, so a
 * missing access cookie here really means "no session".
 */
export async function GET(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!access) return NextResponse.json({ user: null }, { headers: PRIVATE });

  let upstream: Response;
  try {
    upstream = await fetch(`${backendOrigin()}/api/v1/auth/me/`, {
      headers: upstreamHeaders(request.headers, access),
      cache: "no-store",
    });
  } catch {
    // Django unreachable: say so, rather than signing the customer out.
    return NextResponse.json({ detail: "The service is temporarily unavailable." }, { status: 503, headers: PRIVATE });
  }

  if (upstream.status === 401) {
    // Revoked (password changed, signed out elsewhere): drop the dead cookies.
    const response = NextResponse.json({ user: null }, { headers: PRIVATE });
    clearSessionCookies(response);
    return response;
  }
  if (!upstream.ok) {
    return NextResponse.json({ detail: "Could not check your session." }, { status: 502, headers: PRIVATE });
  }
  return NextResponse.json({ user: await upstream.json() }, { headers: PRIVATE });
}
