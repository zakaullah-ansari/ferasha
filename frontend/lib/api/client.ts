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
  Category,
  CheckoutQuote,
  DeliveryAddress,
  Facets,
  NewReview,
  OrderDetail,
  Paginated,
  PlacedOrder,
  ProductDetail,
  ProductSummary,
  Registration,
  Review,
  ReviewSummary,
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

/** A repeated key (`?occasion=eid&occasion=nikah`) is how the API takes several values. */
type QueryParams =
  | URLSearchParams
  | Readonly<Record<string, string | number | readonly string[] | undefined>>;

function toQuery(params: QueryParams): string {
  const query = new URLSearchParams();
  const entries = params instanceof URLSearchParams ? params.entries() : Object.entries(params);
  for (const [key, value] of entries) {
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item !== undefined && item !== "") query.append(key, String(item));
    }
  }
  return query.size > 0 ? `?${query}` : "";
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
  readonly method?: "GET" | "POST" | "PATCH" | "DELETE";
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

/** The session check already on its way, shared by everyone who asks meanwhile. */
let inFlightMe: Promise<SessionUser | null> | null = null;

export const api = {
  listProducts(params: QueryParams = {}, options?: RequestOptions): Promise<Paginated<ProductSummary>> {
    return get<Paginated<ProductSummary>>(`/api/v1/catalog/products/${toQuery(params)}`, options);
  },

  getFacets(params: QueryParams = {}): Promise<Facets> {
    return get<Facets>(`/api/v1/catalog/products/facets/${toQuery(params)}`);
  },

  getCategory(slug: string): Promise<Category> {
    return get<Category>(`/api/v1/catalog/categories/${encodeURIComponent(slug)}/`);
  },

  getReviews(productId: string): Promise<Paginated<Review>> {
    return get<Paginated<Review>>(`/api/v1/reviews/${toQuery({ product: productId })}`);
  },

  getReviewSummary(productId: string): Promise<ReviewSummary> {
    return get<ReviewSummary>(`/api/v1/reviews/summary/${toQuery({ product: productId })}`);
  },

  /** Signed in only. The review waits for the atelier's moderation before anyone else sees it. */
  createReview(review: NewReview): Promise<Review> {
    return send("/api/v1/reviews/", { method: "POST", body: review });
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
    /**
     * The signed-in customer, or null for a guest. A guest is answered by the
     * storefront without asking Django (no 401). Callers asking at the same
     * moment (header, review form) share one request.
     */
    me(): Promise<SessionUser | null> {
      inFlightMe ??= send<{ user: SessionUser | null }>("/api/session/me", {}, true)
        .then((body) => body.user)
        .finally(() => {
          inFlightMe = null;
        });
      return inFlightMe;
    },
    signIn(credentials: { email: string; password: string; remember?: boolean }): Promise<{ user: SessionUser }> {
      return send("/api/session/login", { method: "POST", body: credentials }, true);
    },
    register(details: Registration): Promise<{ user: SessionUser }> {
      return send("/api/session/register", { method: "POST", body: details }, true);
    },
    /** Transport only: call lib/sign-out, which also forgets measurements kept in this browser. */
    signOut(): Promise<void> {
      return send("/api/session/logout", { method: "POST" }, true);
    },
    updateProfile(details: { full_name: string; phone: string }): Promise<SessionUser> {
      return send("/api/v1/auth/me/", { method: "PATCH", body: details });
    },
    /** Always "accepted": the answer never reveals whether an account exists. */
    requestPasswordReset(email: string): Promise<{ detail: string }> {
      return send("/api/v1/auth/password/reset/request/", { method: "POST", body: { email } });
    },
    resetPassword(details: { token: string; new_password: string; new_password_confirm: string }): Promise<{ detail: string }> {
      return send("/api/v1/auth/password/reset/confirm/", { method: "POST", body: details });
    },
    /** Always "accepted": the answer never reveals whether an account exists. */
    requestEmailVerification(email: string): Promise<{ detail: string }> {
      return send("/api/v1/auth/email/verify/request/", { method: "POST", body: { email } });
    },
    confirmEmail(token: string): Promise<{ detail: string }> {
      return send("/api/v1/auth/email/verify/confirm/", { method: "POST", body: { token } });
    },
    /** Revokes every session, this one included: the caller must sign in again. */
    changePassword(details: {
      current_password: string;
      new_password: string;
      new_password_confirm: string;
    }): Promise<{ detail: string }> {
      return send("/api/v1/auth/password/change/", { method: "POST", body: details });
    },
    /**
     * Closes the account and erases its data (DPDP Act s.12). Needs the
     * password; refused with 409 while an order is in progress. Every session
     * is revoked, this one included.
     */
    deleteAccount(password: string): Promise<{ detail: string }> {
      return send("/api/v1/auth/me/delete/", { method: "POST", body: { password } });
    },
  },

  cart: {
    /**
     * Make the server cart exactly the browser bag, in one transaction.
     * Returns the variant ids the server refused (sold out, unpublished).
     */
    /**
     * Make the server cart exactly the browser bag. A bespoke line carries its
     * measurements; the server validates them again and answers 400 (never a
     * silent skip) when the atelier cannot cut from them.
     */
    replace(
      items: ReadonlyArray<{
        variant_id: string;
        quantity: number;
        bespoke?: { measurements: Record<string, number>; preferences: Record<string, string> };
      }>,
    ): Promise<{ skipped: string[] }> {
      return send("/api/v1/cart/merge/", { method: "POST", body: { items, replace: true } });
    },
  },

  orders: {
    /** Back office: move an order to its next stage. The API's state machine has the final say (409). */
    transition(orderNumber: string, status: string, reason = ""): Promise<OrderDetail> {
      return send(`/api/v1/orders/${encodeURIComponent(orderNumber)}/transition/`, {
        method: "POST",
        body: { status, reason },
      });
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
