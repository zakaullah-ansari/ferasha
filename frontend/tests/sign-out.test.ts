import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { FIT_DRAFT_KEY } from "@/lib/fit-draft";
import { signOut } from "@/lib/sign-out";
import { useCartStore } from "@/store/useCartStore";

import { BAG, BESPOKE_LINE } from "./fixtures/commerce";

describe("signing out on a shared computer", () => {
  beforeEach(() => {
    window.localStorage.setItem(FIT_DRAFT_KEY, JSON.stringify({ bust: 36 }));
    useCartStore.setState({ items: [BAG[0]!, BESPOKE_LINE] });
  });

  it("forgets every measurement kept in this browser, keeps ready-made pieces", async () => {
    const request = vi.spyOn(api.session, "signOut").mockResolvedValue(undefined);

    await signOut();

    expect(window.localStorage.getItem(FIT_DRAFT_KEY)).toBeNull();
    expect(useCartStore.getState().items).toEqual([BAG[0]]);
    expect(JSON.stringify(window.localStorage)).not.toContain('"bust"');
    expect(request).toHaveBeenCalledOnce();
  });

  it("forgets them even when the network call fails", async () => {
    vi.spyOn(api.session, "signOut").mockRejectedValue(new Error("offline"));

    await signOut();

    expect(useCartStore.getState().items.some((item) => item.bespoke)).toBe(false);
    expect(window.localStorage.getItem(FIT_DRAFT_KEY)).toBeNull();
  });
});
