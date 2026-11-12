import type { NextRequest } from "next/server";

import {
  OAUTH_COOKIE,
  type OAuthFailure,
  failureFor,
  failurePath,
  oauthCookieOptions,
  parsePending,
} from "@/lib/oauth";
import { redirectWithin } from "@/lib/oauth-server";
import { backendOrigin, upstreamHeaders, writeSessionCookies } from "@/lib/session";

/**
 * GET /api/session/oauth/{provider}/callback?code=...&state=...
 *
 * Where the provider returns the browser. The pending cookie is spent on
 * every outcome, so a code or state can never be replayed from here.
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  const query = request.nextUrl.searchParams;
  const pending = parsePending(request.cookies.get(OAUTH_COOKIE)?.value);
  const next = pending?.next ?? "/";

  const finish = (target: string) => {
    const response = redirectWithin(target);
    response.cookies.set(OAUTH_COOKIE, "", { ...oauthCookieOptions(), maxAge: 0 });
    return response;
  };
  const fail = (reason: OAuthFailure) => finish(failurePath(reason, next));

  // The person pressed "Cancel" at the provider: not an error worth alarming over.
  if (query.get("error") === "access_denied") return fail("oauth-cancelled");

  const code = query.get("code");
  const state = query.get("state");
  if (!pending || pending.provider !== provider || !code || !state || state !== pending.state) {
    return fail("oauth-failed");
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${backendOrigin()}/api/v1/auth/social/${provider}/`, {
      method: "POST",
      headers: upstreamHeaders(request.headers),
      body: JSON.stringify({ code, code_verifier: pending.verifier, nonce: pending.nonce }),
      cache: "no-store",
    });
  } catch {
    return fail("oauth-failed");
  }
  if (!upstream.ok) return fail(failureFor(upstream.status));

  const data = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
  if (typeof data.access !== "string" || typeof data.refresh !== "string") return fail("oauth-failed");

  const response = finish(pending.next);
  writeSessionCookies(response, { access: data.access, refresh: data.refresh });
  return response;
}
