import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  backendOrigin,
  clearSessionCookies,
  upstreamHeaders,
} from "@/lib/session";

/**
 * POST /api/session/logout - revoke the refresh token and drop the cookies.
 *
 * The middleware has already refreshed an expired access token on the way in,
 * so the revoke call is authenticated. Cookies are cleared even if Django is
 * unreachable: signing out must always work from the customer's side.
 */
export async function POST(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;

  if (access && refresh) {
    await fetch(`${backendOrigin()}/api/v1/auth/logout/`, {
      method: "POST",
      headers: upstreamHeaders(request.headers, access),
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    }).catch(() => undefined);
  }

  const response = new NextResponse(null, { status: 204 });
  clearSessionCookies(response);
  return response;
}
