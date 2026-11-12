/** Route-handler side of sign-in with a provider. Never import from a component. */

import { NextResponse } from "next/server";

/**
 * A redirect within the shop, by path. Relative on purpose (RFC 9110 allows
 * it): the browser resolves it against the address it actually used, which
 * the server cannot know reliably behind a proxy or a 0.0.0.0 dev bind.
 */
export function redirectWithin(path: string): NextResponse {
  return new NextResponse(null, { status: 303, headers: { Location: path } });
}
