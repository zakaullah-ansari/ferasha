import { describe, expect, it } from "vitest";

import { HELP } from "@/lib/navigation";
import { POLICIES, policy } from "@/lib/policies";

describe("help pages", () => {
  it("every footer help link leads to a page that exists", () => {
    for (const { href } of HELP) {
      if (href === "/contact") continue;
      const slug = href.replace("/policies/", "");
      expect(policy(slug), href).toBeDefined();
    }
  });

  it("every policy is linked from the footer", () => {
    const linked = new Set(HELP.map((link) => link.href));
    expect(POLICIES.filter((p) => !linked.has(`/policies/${p.slug}`))).toEqual([]);
  });

  it("states the delivery terms checkout actually charges", () => {
    const shipping = JSON.stringify(policy("shipping"));
    expect(shipping).toContain("Free delivery to any address in Maharashtra");
    expect(shipping).toContain("₹150");
  });
});
