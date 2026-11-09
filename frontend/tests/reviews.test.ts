import { describe, expect, it } from "vitest";

import type { ReviewSummary } from "@/lib/api/types";
import { coverageAsDescribed, usualFit } from "@/lib/reviews";

const SUMMARY: ReviewSummary = {
  count: 4,
  average: "4.3",
  distribution: { "1": 0, "2": 0, "3": 1, "4": 1, "5": 2 },
  fit: { ran_small: 1, true_to_size: 3, ran_large: 0 },
  modesty_as_described: { yes: 2, no: 1 },
};

describe("review summary", () => {
  it("names the fit most reviewers report", () => {
    expect(usualFit(SUMMARY)).toBe("true_to_size");
  });

  it("says nothing about fit when nobody answered", () => {
    expect(usualFit({ ...SUMMARY, fit: { ran_small: 0, true_to_size: 0, ran_large: 0 } })).toBeNull();
  });

  it("counts coverage only among those who answered", () => {
    expect(coverageAsDescribed(SUMMARY)).toBe(67);
    expect(coverageAsDescribed({ ...SUMMARY, modesty_as_described: { yes: 0, no: 0 } })).toBeNull();
  });
});
