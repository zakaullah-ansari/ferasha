import { describe, expect, it } from "vitest";

import { isCurrentLink } from "@/lib/nav-active";

const params = (query: string) => new URLSearchParams(query);

describe("isCurrentLink", () => {
  it("matches a link whose every parameter the page shares, ignoring extra ones", () => {
    expect(isCurrentLink("/products?category=suits", "/products", params("category=suits&sort=new"))).toBe(true);
  });

  it("does not light one category on another's listing", () => {
    expect(isCurrentLink("/products?category=suits", "/products", params("category=bridal"))).toBe(false);
  });

  it("does not light a filtered link on the unfiltered listing or another path", () => {
    expect(isCurrentLink("/products?category=suits", "/products", params(""))).toBe(false);
    expect(isCurrentLink("/products?category=suits", "/products/velvet-gharara", params("category=suits"))).toBe(false);
  });
});
