/**
 * Session primitives shared by `middleware.ts` and the `/api/session/*`
 * route handlers.
 *
 * The browser never holds a readable token. Django's JWTs live in httpOnly
 * cookies, so injected script (XSS) cannot exfiltrate them, and the
 * middleware turns them into an Authorization header on the way to the API.
 * Cookie-borne credentials bring CSRF back into play; `isSameOrigin` is the
 * guard, applied to every state-changing request that carries them.
 *
 * Pure functions only: this runs in both the edge (middleware) and Node
 * (route handler) runtimes.
 */

export const ACCESS_COOKIE = "ferasha_access";
export const REFRESH_COOKIE = "ferasha_refresh";

/** Mirror SIMPLE_JWT in backend-core/config/settings.py. */
export const ACCESS_MAX_AGE_SECONDS = 30 * 60;
export const REFRESH_MAX_AGE_SECONDS = 14 * 24 * 60 * 60;

/** Refresh slightly early so a token cannot expire between here and Django. */
const EXPIRY_SKEW_SECONDS = 30;

export function backendOrigin(): string {
  return process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
}

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    // Lax: sent on top-level navigations (so arriving from an email link
    // works) but not on cross-site POSTs.
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}

/** `exp` (seconds since epoch) from a JWT, or null if it cannot be read. */
export function tokenExpiry(jwt: string): number | null {
  const payload = jwt.split(".")[1];
  if (!payload) return null;
  try {
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const exp = (JSON.parse(json) as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp : null;
  } catch {
    return null;
  }
}

/**
 * True when the token is expired or about to be. Only decides *when* to
 * refresh; it does not verify the signature - Django does that on every call.
 */
export function isExpiring(jwt: string, nowMs: number = Date.now()): boolean {
  const exp = tokenExpiry(jwt);
  return exp === null || exp - EXPIRY_SKEW_SECONDS <= nowMs / 1000;
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export function isSafeMethod(method: string): boolean {
  return SAFE_METHODS.has(method.toUpperCase());
}

/**
 * Did this request come from our own pages? Compares the browser-set Origin
 * header with the host the request was addressed to. A missing Origin fails
 * closed: browsers send it on every state-changing fetch and form post.
 */
export function isSameOrigin(headers: Headers): boolean {
  const origin = headers.get("origin");
  if (!origin) return false;
  let originHost: string;
  try {
    originHost = new URL(origin).host;
  } catch {
    return false;
  }
  const hosts = [headers.get("x-forwarded-host"), headers.get("host")].filter(Boolean);
  return hosts.includes(originHost);
}

export interface TokenPair {
  readonly access: string;
  readonly refresh: string;
}

/** Exchange a refresh token for a new pair (Django rotates the refresh). */
export async function refreshTokens(refresh: string): Promise<TokenPair | null> {
  try {
    const response = await fetch(`${backendOrigin()}/api/v1/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    const data = (await response.json()) as Partial<TokenPair>;
    if (!data.access) return null;
    // Without rotation Django returns only `access`; keep the old refresh.
    return { access: data.access, refresh: data.refresh ?? refresh };
  } catch {
    return null;
  }
}

/** Anything with Next's response-cookie API (NextResponse in either runtime). */
interface CookieWriter {
  readonly cookies: {
    set(name: string, value: string, options: ReturnType<typeof cookieOptions>): unknown;
    delete(name: string): unknown;
  };
}

function remainingSeconds(jwt: string, fallback: number): number {
  const exp = tokenExpiry(jwt);
  return exp === null ? fallback : Math.max(0, Math.floor(exp - Date.now() / 1000));
}

export function writeSessionCookies(response: CookieWriter, pair: TokenPair): void {
  response.cookies.set(ACCESS_COOKIE, pair.access, cookieOptions(ACCESS_MAX_AGE_SECONDS));
  response.cookies.set(
    REFRESH_COOKIE,
    pair.refresh,
    cookieOptions(remainingSeconds(pair.refresh, REFRESH_MAX_AGE_SECONDS)),
  );
}

export function clearSessionCookies(response: CookieWriter): void {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
}

/**
 * Headers for a server-to-Django call made on a browser's behalf. Forwarding
 * the client address keeps Django's per-IP login throttle per customer
 * rather than one bucket for the whole storefront server.
 */
export function upstreamHeaders(incoming: Headers, accessToken?: string): HeadersInit {
  const forwardedFor = incoming.get("x-forwarded-for") ?? incoming.get("x-real-ip");
  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}
