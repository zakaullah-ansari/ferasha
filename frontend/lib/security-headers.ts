/**
 * HTTP security headers for every storefront response (wired in
 * next.config.ts). Django sets its own for the API and admin; the pages
 * customers actually see come from here.
 *
 * Production only, for good reasons:
 * - framing is refused (clickjacking: an invisible sign-in or "Place order"
 *   page under someone else's buttons) - development previews (e2b) frame
 *   the app;
 * - HSTS pins HTTPS, which would break plain-http localhost.
 *
 * Deliberately not here yet: a full script/style Content-Security-Policy. It
 * needs per-request nonces for Next's inline scripts and a pass over every
 * third party (Razorpay, Google sign-in redirects); a half-right CSP breaks
 * pages silently, so it gets its own change.
 */

export interface Header {
  readonly key: string;
  readonly value: string;
}

export function securityHeaders({ production }: { production: boolean }): Header[] {
  const policy = [
    "base-uri 'self'", // an injected <base> cannot re-point every relative link
    "object-src 'none'", // no plugins
    "form-action 'self'", // forms only post to us
    ...(production ? ["frame-ancestors 'none'"] : []),
  ].join("; ");

  return [
    { key: "Content-Security-Policy", value: policy },
    { key: "X-Content-Type-Options", value: "nosniff" },
    // Full URLs (reset and confirmation tokens) never leave the site.
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), browsing-topics=()" },
    // Isolates the window from pages it opens; popups (payment) still work.
    { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
    ...(production
      ? [
          // Older browsers that ignore frame-ancestors.
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
        ]
      : []),
  ];
}
