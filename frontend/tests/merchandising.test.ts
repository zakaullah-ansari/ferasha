import { describe, expect, it } from "vitest";

import { isNewArrival, NEW_ARRIVAL_DAYS, percentOff } from "@/lib/merchandising";

describe("percentOff", () => {
  it("is null when there is no compare-at price", () => {
    expect(percentOff("4990.00", null)).toBeNull();
  });

  it("rounds down, so the label never overstates the saving", () => {
    expect(percentOff("8000.00", "10000.00")).toBe(20);
    expect(percentOff("6999.00", "9999.00")).toBe(30); // 30.003% -> 30
    expect(percentOff("7000.00", "9999.00")).toBe(29); // 29.993% -> 29, never 30
  });

  it("shows an exact saving exactly (floating point would make 20% read as 19%)", () => {
    expect(percentOff("13592.00", "16990.00")).toBe(20);
  });

  it("is null for a compare-at price that is not higher (bad data never shows a sale)", () => {
    expect(percentOff("5000.00", "5000.00")).toBeNull();
    expect(percentOff("5000.00", "4000.00")).toBeNull();
  });

  it("is null for a saving under 1%, which would read as -0%", () => {
    expect(percentOff("9950.00", "10000.00")).toBeNull();
  });

  it("is null for unparseable input", () => {
    expect(percentOff("abc", "10000.00")).toBeNull();
    expect(percentOff("5000.00", "")).toBeNull();
  });
});

describe("isNewArrival", () => {
  const now = new Date("2026-11-12T12:00:00Z");
  const daysAgo = (days: number) => new Date(now.getTime() - days * 86_400_000).toISOString();

  it("is new inside the window", () => {
    expect(isNewArrival(daysAgo(0), now)).toBe(true);
    expect(isNewArrival(daysAgo(NEW_ARRIVAL_DAYS - 1), now)).toBe(true);
  });

  it("is not new once the window has passed", () => {
    expect(isNewArrival(daysAgo(NEW_ARRIVAL_DAYS + 1), now)).toBe(false);
  });

  it("is not new for a missing or invalid date, or one in the future", () => {
    expect(isNewArrival(undefined, now)).toBe(false);
    expect(isNewArrival("not a date", now)).toBe(false);
    expect(isNewArrival(daysAgo(-2), now)).toBe(false);
  });
});
