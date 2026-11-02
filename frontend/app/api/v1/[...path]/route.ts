import { type NextRequest, NextResponse } from "next/server";

import { ACCESS_COOKIE, backendOrigin } from "@/lib/session";

/**
 * Browser -> Django proxy for /api/v1/*.
 *
 * A route handler rather than a next.config rewrite: cookies the middleware
 * sets when it refreshes a token are dropped on external rewrites, so the
 * browser would keep presenting a refresh token Django has just blacklisted
 * (rotation) and the customer would be signed out mid-checkout. Through a
 * route handler the middleware's cookies reach the browser.
 *
 * By the time this runs the middleware has refreshed an expiring token and
 * applied the CSRF check; here the access cookie becomes a bearer header.
 */

/** Request headers worth forwarding; everything else stays at the edge. */
const FORWARD_REQUEST = ["accept", "accept-language", "content-type", "idempotency-key", "x-forwarded-for"];
/** Response headers the browser should see from Django. */
const FORWARD_RESPONSE = ["content-type", "cache-control", "idempotent-replayed", "retry-after"];

async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname, search } = request.nextUrl;
  const headers = new Headers();
  for (const name of FORWARD_REQUEST) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  if (access) headers.set("authorization", `Bearer ${access}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(`${backendOrigin()}${pathname}${search}`, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "The service is temporarily unavailable." }, { status: 502 });
  }

  const responseHeaders = new Headers();
  for (const name of FORWARD_RESPONSE) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
