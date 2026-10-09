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

import type { Paginated, ProductDetail, ProductSummary, TaxQuote } from "./types";

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
};
