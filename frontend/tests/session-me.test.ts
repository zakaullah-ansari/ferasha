/**
 * GET /api/session/me - "who is signed in?" for the header and review form.
 * A guest is an answer, not an error: no Django call, no 401 in the console.
 */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/session/me/route";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";

function request(cookies: Record<string, string> = {}) {
  const headers = new Headers();
  const jar = Object.entries(cookies).map(([name, value]) => `${name}=${value}`).join("; ");
  if (jar) headers.set("cookie", jar);
  return new NextRequest("https://shop.example/api/session/me", { headers });
}

afterEach(() => vi.unstubAllGlobals());

describe("GET /api/session/me", () => {
  it("answers a guest straight away, without asking Django", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(request());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ user: null });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("cache-control")).toContain("no-store");
  });

  it("returns the signed-in customer", async () => {
    const user = { id: "u1", email: "ayesha@example.com", full_name: "Ayesha Khan", is_back_office: false };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(user), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(request({ [ACCESS_COOKIE]: "a.b.c" }));
    expect(await response.json()).toEqual({ user });
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/api\/v1\/auth\/me\/$/);
    expect(fetchMock.mock.calls[0]?.[1].headers.Authorization).toBe("Bearer a.b.c");
  });

  it("treats a session Django no longer accepts as a guest, and clears it", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
    const response = await GET(request({ [ACCESS_COOKIE]: "stale", [REFRESH_COOKIE]: "stale" }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ user: null });
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe("");
  });

  it("reports an outage as an outage, not as signed out", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    const response = await GET(request({ [ACCESS_COOKIE]: "a.b.c" }));
    expect(response.status).toBe(503);
    expect(response.cookies.get(ACCESS_COOKIE)).toBeUndefined();
  });
});
