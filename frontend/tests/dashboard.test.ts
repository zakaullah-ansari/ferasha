import { describe, expect, it } from "vitest";

import { ADMIN_LINKS } from "@/lib/admin-links";
import { attentionItems, change, ordersHref } from "@/lib/dashboard";
import { formatDay, formatMoment } from "@/lib/format";
import { orderMoves, orderStatus, orderView } from "@/lib/order-status";

import { BACK_OFFICE_ORDER, QUIET_SUMMARY, SUMMARY } from "./fixtures/back-office";

describe("change", () => {
  it("states the size and the direction", () => {
    expect(change(325680, 254880)).toEqual({ percent: 28, direction: "up" });
    expect(change(50, 100)).toEqual({ percent: 50, direction: "down" });
    expect(change(100, 100)).toEqual({ percent: 0, direction: "flat" });
  });

  it("invents no percentage against nothing", () => {
    expect(change(5000, 0)).toBeNull();
  });
});

describe("attentionItems", () => {
  it("lists what waits on the owner, in working order, with where to act", () => {
    const items = attentionItems(SUMMARY);
    expect(items.map((item) => [item.label, item.count])).toEqual([
      ["Paid, ready to start", 3],
      ["Measurements to review", 1],
      ["Packed, ready to ship", 2],
      ["Reviews to moderate", 2],
      ["Photos needing a privacy check", 1],
      ["Sizes running low", 2],
    ]);
    expect(items[0]).toMatchObject({ href: "/dashboard/orders?view=to-start" });
    expect(items.find((item) => item.id === "reviews")).toMatchObject({ href: ADMIN_LINKS.pendingReviews, external: true });
  });

  it("is empty when everything is done; stages the owner does not act on never appear", () => {
    expect(attentionItems(QUIET_SUMMARY)).toEqual([]);
    expect(attentionItems(SUMMARY).map((item) => item.id)).not.toContain("shipped");
  });
});

describe("dates", () => {
  it("shows a calendar date the same in every time zone", () => {
    expect(formatDay("2026-11-05")).toBe("5 Nov");
  });

  it("shows a moment in Mumbai time", () => {
    // 18:30 UTC on 31 Oct is midnight in Mumbai: already 1 November there.
    expect(formatMoment("2026-10-31T18:30:00Z")).toMatch(/^1 Nov/);
    expect(formatMoment(null)).toBe("—");
  });
});

describe("orderMoves", () => {
  it("sends a paid bespoke order to the atelier", () => {
    expect(orderMoves(BACK_OFFICE_ORDER)).toEqual({
      suggested: "in_atelier",
      others: ["measurement_review", "packed"],
      canCancel: true,
    });
  });

  it("sends a paid ready-made order straight to packing", () => {
    const readyMade = { ...BACK_OFFICE_ORDER, lines: [{ ...BACK_OFFICE_ORDER.lines[0]!, is_bespoke: false }] };
    expect(orderMoves(readyMade).suggested).toBe("packed");
  });

  it("never suggests going back, or a move that needs a reason", () => {
    expect(orderMoves({ status: "quality_check", next_statuses: ["packed", "stitching"], lines: [] }).suggested).toBe("packed");
    expect(orderMoves({ status: "delivered", next_statuses: ["return_requested"], lines: [] })).toEqual({
      suggested: undefined,
      others: ["return_requested"],
      canCancel: false,
    });
  });
});

describe("order statuses and views", () => {
  it("speaks to each audience in its own words, and shows unknown statuses as they are", () => {
    expect(orderStatus("quality_check")).toMatchObject({ label: "Quality check", customer: "Final quality check" });
    expect(orderStatus("on_hold").label).toBe("on_hold");
  });

  it("falls back to the first view for an unknown one", () => {
    expect(orderView("atelier").statuses).toContain("stitching");
    expect(orderView("nonsense").id).toBe("to-start");
  });
});

describe("ordersHref", () => {
  it("keeps the view and the search, and leaves page one out", () => {
    expect(ordersHref({ view: "atelier" })).toBe("/dashboard/orders?view=atelier");
    expect(ordersHref({ view: "all", q: "Ayesha Khan", page: 3 })).toBe("/dashboard/orders?view=all&q=Ayesha+Khan&page=3");
  });
});
