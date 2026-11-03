/**
 * Stub the network for a story, so components that call the API render a
 * chosen state (success, error, slow) without a running backend.
 *
 * Use from a story's `beforeEach`; the returned function restores fetch.
 */

export interface MockRoute {
  readonly method?: string;
  /** Matched against the request path, e.g. "/api/v1/checkout/quote/". */
  readonly path: string | RegExp;
  readonly status?: number;
  readonly body?: unknown;
  /** Keeps a request pending, to show loading states. */
  readonly delayMs?: number;
}

export function mockFetch(routes: readonly MockRoute[]): () => void {
  const original = globalThis.fetch;
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, location.origin);
    const method = (init?.method ?? "GET").toUpperCase();
    const route = routes.find(
      (candidate) =>
        (candidate.method ?? "GET").toUpperCase() === method &&
        (typeof candidate.path === "string" ? url.pathname === candidate.path : candidate.path.test(url.pathname)),
    );
    if (route?.delayMs) await new Promise((resolve) => setTimeout(resolve, route.delayMs));
    if (!route) return new Response(JSON.stringify({ detail: "Not mocked" }), { status: 404 });
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), {
      status: route.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  return () => {
    globalThis.fetch = original;
  };
}
