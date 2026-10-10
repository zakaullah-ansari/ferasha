/**
 * Unit conversion tests.
 *
 * The scenario being defended: a customer enters measurements in inches,
 * toggles to cm to compare against a size chart, toggles back, and submits.
 * If the round trip is lossy, the number they submit is not the number they
 * typed, and a bespoke garment is cut wrong.
 */

import { describe, expect, it } from "vitest";

import {
  CM_PER_INCH,
  cmToInch,
  convert,
  convertRecord,
  describeMeasurement,
  fromDisplay,
  inchToCm,
  toDisplay,
} from "@/lib/units";

describe("conversion constants", () => {
  it("uses the exact international inch", () => {
    expect(CM_PER_INCH).toBe(2.54);
  });

  it("converts known values", () => {
    expect(cmToInch(2.54)).toBeCloseTo(1, 10);
    expect(inchToCm(1)).toBeCloseTo(2.54, 10);
    expect(cmToInch(91.44)).toBeCloseTo(36, 10);
  });
});

describe("round tripping is lossless", () => {
  // Realistic bust/waist/hip/length values plus awkward decimals.
  const values = [
    81.28, 86.36, 91.44, 96.52, 101.6, 71.12, 66.04, 106.68, 114.3, 142.24,
    33.333, 0.1, 1.005, 2.675, 99.995,
  ];

  it.each(values)("cm %s survives cm -> inch -> cm", (cm) => {
    expect(inchToCm(cmToInch(cm))).toBeCloseTo(cm, 10);
  });

  it.each(values)("value %s survives display -> parse at full precision", (cm) => {
    // The stored value is never rounded on the way in.
    expect(fromDisplay(cmToInch(cm), "inch", "cm")).toBeCloseTo(cm, 10);
  });

  it("survives repeated unit toggling", () => {
    // Twenty toggles is well beyond what any user would do, and is exactly
    // the kind of thing that exposes compounding rounding.
    let value = 86.36;
    for (let i = 0; i < 20; i += 1) {
      value = inchToCm(cmToInch(value));
    }
    expect(value).toBeCloseTo(86.36, 8);
  });
});

describe("display formatting", () => {
  it("rounds centimetres to one decimal", () => {
    expect(toDisplay(86.3612, "cm", "cm")).toBe(86.4);
    expect(toDisplay(86.0, "cm", "cm")).toBe(86);
  });

  it("rounds inches to two decimals", () => {
    expect(toDisplay(91.44, "cm", "inch")).toBe(36);
    expect(toDisplay(86.36, "cm", "inch")).toBe(34);
  });

  it("handles the binary floating point .5 boundary correctly", () => {
    // The classic (1.005).toFixed(2) === "1.00" trap.
    expect(toDisplay(1.005, "cm", "cm")).toBe(1);
    expect(toDisplay(2.55, "cm", "cm")).toBe(2.6);
    expect(toDisplay(0.05, "cm", "cm")).toBe(0.1);
  });

  it("does not let rounding leak back into the stored value", () => {
    const stored = 86.3649;
    const shown = toDisplay(stored, "cm", "cm");
    expect(shown).toBe(86.4);
    expect(fromDisplay(stored, "cm", "cm")).toBe(stored);
    expect(fromDisplay(stored, "cm", "cm")).not.toBe(shown);
  });
});

describe("the canonical-unit mismatch that broke every bespoke order", () => {
  /*
   * Regression. The units module once assumed canonical centimetres while the
   * fit contract is canonical inches, so a 36in bust was stored as 91.44 —
   * read back as inches. Both modules were individually correct.
   *
   * These assertions pin the property that makes that impossible: a
   * same-unit conversion is the identity, so no amount of plumbing can
   * introduce a silent 2.54x factor.
   */
  it.each(["cm", "inch"] as const)("%s -> %s is the identity", (unit) => {
    for (const value of [1, 36, 91.44, 0.125]) {
      expect(convert(value, unit, unit)).toBe(value);
      expect(fromDisplay(value, unit, unit)).toBe(value);
    }
  });

  it("a value entered in inches and stored in inches is unchanged", () => {
    expect(fromDisplay(36, "inch", "inch")).toBe(36);
  });

  it("a value stored in inches and shown in inches is unchanged", () => {
    expect(toDisplay(36, "inch", "inch")).toBe(36);
  });

  it("only converts when the units genuinely differ", () => {
    expect(fromDisplay(36, "cm", "inch")).toBeCloseTo(14.173, 3);
    expect(fromDisplay(36, "inch", "cm")).toBeCloseTo(91.44, 3);
  });
});

describe("describeMeasurement", () => {
  it("labels the unit for screen readers", () => {
    expect(describeMeasurement(86.36, "cm", "cm")).toBe("86.4 cm");
    expect(describeMeasurement(86.36, "cm", "inch")).toBe("34 in");
  });
});

describe("convertRecord", () => {
  it("converts a whole measurement set", () => {
    const canonical = { bust: 91.44, waist: 71.12, hip: 96.52 };
    expect(convertRecord(canonical, "cm", "inch")).toEqual({
      bust: 36,
      waist: 28,
      hip: 38,
    });
  });

  it("is identity-ish in cm, modulo display rounding", () => {
    const canonical = { bust: 91.4, waist: 71.1 };
    expect(convertRecord(canonical, "cm", "cm")).toEqual(canonical);
  });
});

describe("hostile input", () => {
  it.each([NaN, Infinity, -Infinity])("rejects %s", (bad) => {
    expect(() => cmToInch(bad)).toThrow(TypeError);
    expect(() => toDisplay(bad, "cm", "cm")).toThrow(TypeError);
  });

  it("rejects non-numbers coming from an uncontrolled input", () => {
    // Number("") is 0, but Number("abc") is NaN — the realistic failure when
    // a text input is read without validation.
    expect(() => inchToCm(Number("abc"))).toThrow(TypeError);
  });

  it("accepts zero and negative values without throwing", () => {
    // Validation of plausible ranges is the schema's job, not the
    // converter's. Mixing the two responsibilities makes both harder to test.
    expect(cmToInch(0)).toBe(0);
    expect(() => cmToInch(-5)).not.toThrow();
  });
});
