/**
 * Typed fetch wrapper for the Ferasha API.
 *
 * Deployment rule that drives the design: the browser must never be handed an
 * absolute backend URL. In every environment that matters — the sandbox
 * preview, a container, a phone on a LAN — "localhost:8000" resolves to the
 * user's own machine, not the API. So browser calls use a relative `/api/...`
 * path which Next rewrites to the backend server-side (see `next.config.ts`).
 *
 * Server Components run inside the container and must use an absolute URL,
 * because a relative path has no origin to resolve against there.
 */

import type {
  CheckoutQuote,
  DeliveryAddress,
  Paginated,
  PlacedOrder,
  ProductDetail,
  ProductSummary,
  Registration,
  SessionUser,
  TaxQuote,
} from "./types";

/** Server-side origin. Never shipped to the browser. */
const SERVER_ORIGIN = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const isServer = typeof window === "undefined";

function url(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return isServer ? `${SERVER_ORIGIN}${clean}` : clean;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    message: string,
    /** Only set for 4xx from endpoints whose messages are customer-safe. */
    readonly body?: Readonly<Record<string, unknown>>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  /** ISR revalidation window in seconds. `0` disables caching. */
  readonly revalidate?: number;
  readonly signal?: AbortSignal;
}

async function get<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { revalidate = 60, signal } = options;

  const response = await fetch(url(path), {
    signal,
    headers: { Accept: "application/json" },
    // Catalogue reads are cacheable; anything authenticated must pass 0.
    next: revalidate > 0 ? { revalidate } : undefined,
    cache: revalidate > 0 ? undefined : "no-store",
  });

  if (!response.ok) {
    // Deliberately does not include the response body: an upstream error can
    // contain internal detail, and it would end up rendered in a page.
    throw new ApiError(
      response.status,
      path,
      `Request to ${path} failed with ${response.status}.`,
    );
  }

  return (await response.json()) as T;
}

interface SendOptions {
  readonly method?: "GET" | "POST" | "DELETE";
  readonly body?: unknown;
  /** Sent as Idempotency-Key. Reuse the same key when retrying one attempt. */
  readonly idempotencyKey?: string;
}

/**
 * Browser call to a signed-in endpoint.
 *
 * No token handling here: the session lives in httpOnly cookies that page
 * JavaScript cannot read, and `middleware.ts` turns them into an
 * Authorization header on the way to Django (refreshing it when it expires).
 *
 * One retry on 401: two requests that both find the access token expired race
 * to refresh it; the loser is rejected, but by then the winner's response has
 * set the new cookie, so a single retry succeeds.
 *
 * Checkout and cart endpoints return customer-safe 4xx messages (stock, price
 * changes), so the body is kept on the error; 5xx bodies are never surfaced.
 */
async function send<T>(path: string, options: SendOptions = {}, retried = false): Promise<T> {
  const { method = "GET", body, idempotencyKey } = options;
  const response = await fetch(url(path), {
    method,
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
    cache: "no-store",
  });
  if (response.status === 401 && !retried) return send<T>(path, options, true);
  if (!response.ok) {
    const detail =
      response.status < 500
        ? ((await response.json().catch(() => undefined)) as Record<string, unknown> | undefined)
        : undefined;
    const message =
      typeof detail?.detail === "string" ? detail.detail : `Request to ${path} failed.`;
    throw new ApiError(response.status, path, message, detail);
  }
  return response.status === 204 || response.status === 205
    ? (undefined as T)
    : ((await response.json()) as T);
}

export const api = {
  listProducts(
    params: Readonly<Record<string, string | number | undefined>> = {},
  ): Promise<Paginated<ProductSummary>> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    const suffix = query.size > 0 ? `?${query}` : "";
    return get<Paginated<ProductSummary>>(`/api/v1/catalog/products/${suffix}`);
  },

  getProduct(slug: string): Promise<ProductDetail> {
    return get<ProductDetail>(`/api/v1/catalog/products/${encodeURIComponent(slug)}/`);
  },

  /** Tax is never cached: the rate depends on the destination. */
  async quoteTax(body: unknown): Promise<TaxQuote> {
    const response = await fetch(url("/api/v1/tax/quote/"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!response.ok) {
      throw new ApiError(response.status, "/api/v1/tax/quote/", "Tax quote failed.");
    }
    return (await response.json()) as TaxQuote;
  },

  // Session calls pass retried=true: a 401 from a wrong password is final, and
  // retrying would spend the login rate limit twice.
  session: {
    /** The signed-in customer, or null for a guest. */
    async me(): Promise<SessionUser | null> {
      try {
        return await send<SessionUser>("/api/v1/auth/me/", {}, true);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    signIn(credentials: { email: string; password: string }): Promise<{ user: SessionUser }> {
      return send("/api/session/login", { method: "POST", body: credentials }, true);
    },
    register(details: Registration): Promise<{ user: SessionUser }> {
      return send("/api/session/register", { method: "POST", body: details }, true);
    },
    signOut(): Promise<void> {
      return send("/api/session/logout", { method: "POST" }, true);
    },
  },

  cart: {
    /**
     * Make the server cart exactly the browser bag, in one transaction.
     * Returns the variant ids the server refused (sold out, unpublished).
     */
    replace(
      items: ReadonlyArray<{ variant_id: string; quantity: number }>,
    ): Promise<{ skipped: string[] }> {
      return send("/api/v1/cart/merge/", { method: "POST", body: { items, replace: true } });
    },
  },

  checkout: {
    /** Price the signed-in customer's bag for an address. No side effects. */
    quote(address: DeliveryAddress): Promise<CheckoutQuote> {
      return send("/api/v1/checkout/quote/", { method: "POST", body: { address } });
    },

    /**
     * Place the order. `expectedGrandTotal` is the total the customer saw; a
     * change since then is refused with 409 and a fresh quote on `error.body`.
     */
    placeOrder(
      address: DeliveryAddress,
      expectedGrandTotal: string,
      idempotencyKey: string,
    ): Promise<PlacedOrder> {
      return send("/api/v1/checkout/place-order/", {
        method: "POST",
        body: { address, expected_grand_total: expectedGrandTotal },
        idempotencyKey,
      });
    },
  },
};
