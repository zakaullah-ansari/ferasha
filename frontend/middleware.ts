import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearSessionCookies,
  isExpiring,
  isSafeMethod,
  isSameOrigin,
  refreshTokens,
  writeSessionCookies,
} from "@/lib/session";

/**
 * Session bridge between httpOnly cookies and Django's bearer tokens.
 *
 * 1. CSRF: a state-changing request that carries the session cookies (or
 *    starts a session) must come from our own origin.
 * 2. Refresh: an expiring access token is exchanged before the request goes
 *    on, and the new pair is set on both the response (for the browser) and
 *    the forwarded request (so this render already sees it).
 *
 * The bearer header itself is added by the /api/v1 proxy route, which reads
 * the (possibly just refreshed) access cookie this middleware forwards.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isApi = pathname.startsWith("/api/v1/");
  const isSessionEndpoint = pathname.startsWith("/api/session/");
  let access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  const carriesSession = Boolean(access || refresh);

  if (
    !isSafeMethod(request.method) &&
    (isSessionEndpoint || (isApi && carriesSession)) &&
    !isSameOrigin(request.headers)
  ) {
    return NextResponse.json({ detail: "Cross-site request refused." }, { status: 403 });
  }

  let rotated: { access: string; refresh: string } | null = null;
  let refreshExpired = false;
  if (refresh && (!access || isExpiring(access))) {
    rotated = await refreshTokens(refresh);
    if (rotated) {
      access = rotated.access;
    } else {
      // A refresh can also fail because a parallel request rotated it a
      // moment ago; its response is setting fresh cookies, so clear ours
      // only when the refresh token itself has run out.
      refreshExpired = isExpiring(refresh);
      access = undefined;
    }
  }

  // Mirror any session change onto the forwarded request too, so the page or
  // proxy handling *this* request already sees it.
  const headers = new Headers(request.headers);
  if (rotated) {
    request.cookies.set(ACCESS_COOKIE, rotated.access);
    request.cookies.set(REFRESH_COOKIE, rotated.refresh);
    headers.set("cookie", request.cookies.toString());
  } else if (refreshExpired) {
    request.cookies.delete(ACCESS_COOKIE);
    request.cookies.delete(REFRESH_COOKIE);
    headers.set("cookie", request.cookies.toString());
  }

  const response = NextResponse.next({ request: { headers } });
  if (rotated) writeSessionCookies(response, rotated);
  else if (refreshExpired) clearSessionCookies(response);
  return response;
}

export const config = {
  matcher: ["/api/v1/:path*", "/api/session/:path*", "/checkout/:path*", "/orders/:path*", "/account/:path*"],
};
