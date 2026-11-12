import { type NextRequest, NextResponse } from "next/server";

import { safeNextPath } from "@/lib/api/server";
import {
  OAUTH_COOKIE,
  failurePath,
  isProviderId,
  oauthCookieOptions,
  serializePending,
} from "@/lib/oauth";
import { redirectWithin } from "@/lib/oauth-server";
import { backendOrigin, upstreamHeaders } from "@/lib/session";

/**
 * GET /api/session/oauth/{provider}/start?next=/checkout
 *
 * Asks Django for a fresh provider URL, keeps the one-time secrets in an
 * httpOnly cookie, and sends the browser on to the provider.
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  const next = safeNextPath(request.nextUrl.searchParams.get("next") ?? undefined);
  const fail = () => redirectWithin(failurePath("oauth-failed", next));
  if (!isProviderId(provider)) return fail();

  let data: Record<string, unknown>;
  try {
    const upstream = await fetch(`${backendOrigin()}/api/v1/auth/social/${provider}/authorize/`, {
      method: "POST",
      headers: upstreamHeaders(request.headers),
      cache: "no-store",
    });
    if (!upstream.ok) return fail();
    data = (await upstream.json()) as Record<string, unknown>;
  } catch {
    return fail();
  }

  const { authorization_url: url, state, code_verifier: verifier, nonce } = data;
  if (
    typeof url !== "string" ||
    !url.startsWith("https://") ||
    typeof state !== "string" ||
    typeof verifier !== "string" ||
    typeof nonce !== "string"
  ) {
    return fail();
  }

  const response = NextResponse.redirect(url);
  response.cookies.set(
    OAUTH_COOKIE,
    serializePending({ provider, state, verifier, nonce, next }),
    oauthCookieOptions(),
  );
  return response;
}
