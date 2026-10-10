/**
 * The frontend's validation must match the backend's, exactly.
 *
 * Two failure modes this guards, both of which have shipped in real stores:
 *
 *  - Frontend *stricter* than backend: a customer with a legitimate
 *    measurement is blocked from ordering and has no recourse.
 *  - Frontend *looser* than backend: the customer completes a long form and
 *    is rejected on submit, or the value slips through and a tailor cuts
 *    cloth from a typo.
 *
 * The contract JSON is generated from `apps/tailoring/validators.py`. This
 * suite reads the Python file directly and asserts the JSON still describes
 * it, so editing the Python without regenerating fails the build.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import contract from "@/lib/api/fit-contract.json";
import {
  CROSS_FIELD_RULES,
  MEASUREMENT_NAMES,
  MEASUREMENT_RANGES,
  fitProfileSchema,
  rangeIn,
  requiredFor,
} from "@/lib/api/fit-schema";
import { CM_PER_INCH } from "@/lib/units";

const VALIDATORS_PY = join(
  process.cwd(),
  "../backend-core/apps/tailoring/validators.py",
);

function pythonRanges(): Record<string, { min: number; max: number }> {
  const source = readFileSync(VALIDATORS_PY, "utf8");
  const block = source.slice(
    source.indexOf("MEASUREMENT_RANGES"),
    source.indexOf("REQUIRED_BY_GARMENT"),
  );
  const pattern =
    /"(\w+)":\s*Range\(Decimal\("([\d.]+)"\),\s*Decimal\("([\d.]+)"\)/g;
  const found: Record<string, { min: number; max: number }> = {};
  for (const match of block.matchAll(pattern)) {
    found[match[1]!] = { min: Number(match[2]), max: Number(match[3]) };
  }
  return found;
}

function pythonRequired(): Record<string, string[]> {
  const source = readFileSync(VALIDATORS_PY, "utf8");
  const start = source.indexOf("REQUIRED_BY_GARMENT");
  const block = source.slice(start, source.indexOf("\n}\n", start));
  const found: Record<string, string[]> = {};
  for (const match of block.matchAll(/"(\w+)":\s*\(([^)]*)\)/g)) {
    const fields = [...match[2]!.matchAll(/"(\w+)"/g)].map((m) => m[1]!);
    found[match[1]!] = fields;
  }
  return found;
}

describe("the generated contract is current", () => {
  const fromPython = pythonRanges();

  it("found ranges in the Python source (guards the parser itself)", () => {
    // If the regex silently matches nothing, every assertion below passes
    // vacuously. Anchor on a value we know exists.
    expect(Object.keys(fromPython).length).toBeGreaterThan(15);
    expect(fromPython.bust).toEqual({ min: 24, max: 70 });
  });

  it("covers exactly the measurements Python defines", () => {
    expect(new Set(MEASUREMENT_NAMES)).toEqual(new Set(Object.keys(fromPython)));
  });

  it.each(Object.entries(pythonRanges()))(
    "%s has the same range as the backend",
    (name, range) => {
      expect(MEASUREMENT_RANGES[name as never]).toMatchObject({
        min: range.min,
        max: range.max,
      });
    },
  );

  it("mirrors the required-field map", () => {
    const fromPy = pythonRequired();
    for (const [garment, fields] of Object.entries(fromPy)) {
      expect(contract.requiredByGarment[garment as never]).toEqual(fields);
    }
  });

  it("declares inches as the canonical unit", () => {
    // Every range number is meaningless without this.
    expect(contract.unit).toBe("inch");
  });
});

describe("range conversion", () => {
  it("returns inches unchanged", () => {
    expect(rangeIn("bust", "inch")).toMatchObject({ min: 24, max: 70 });
  });

  it("converts to centimetres for a cm-entering customer", () => {
    const cm = rangeIn("bust", "cm");
    expect(cm.min).toBeCloseTo(24 * CM_PER_INCH, 6);
    expect(cm.max).toBeCloseTo(70 * CM_PER_INCH, 6);
  });
});

describe("per-garment schemas", () => {
  it("requires what a suit cannot be cut without", () => {
    expect(requiredFor("suit_set")).toEqual([
      "bust",
      "waist",
      "hip",
      "shoulder",
      "kameez_length",
      "sleeve_length",
    ]);
  });

  it("requires farshi flare for a farshi palazzo", () => {
    // The measurement that makes the garment what it is.
    expect(requiredFor("farshi_palazzo")).toContain("farshi_flare");
  });

  it("accepts a complete, plausible suit profile", () => {
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 36,
      waist: 30,
      hip: 38,
      shoulder: 15,
      kameez_length: 42,
      sleeve_length: 22,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a profile missing a required measurement", () => {
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 36,
      waist: 30,
      hip: 38,
      shoulder: 15,
      kameez_length: 42,
      // sleeve_length omitted
    });
    expect(result.success).toBe(false);
  });

  it("allows optional measurements to be absent", () => {
    const result = fitProfileSchema("palazzo").safeParse({
      waist: 30,
      hip: 38,
      trouser_length: 40,
    });
    expect(result.success).toBe(true);
  });
});

describe("unit-confusion guards", () => {
  it("rejects centimetres typed into an inch field", () => {
    // 91cm is a perfectly normal bust — in centimetres. As inches it is
    // beyond any human, and it is the single most likely data-entry error.
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 91,
      waist: 76,
      hip: 97,
      shoulder: 38,
      kameez_length: 107,
      sleeve_length: 56,
    });
    expect(result.success).toBe(false);
  });

  it("explains the likely cause in the message", () => {
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 91,
      waist: 30,
      hip: 38,
      shoulder: 15,
      kameez_length: 42,
      sleeve_length: 22,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const message = result.error.issues.map((i) => i.message).join(" ");
      expect(message).toMatch(/centimetres/i);
    }
  });

  it("does not police unusual but real body sizes", () => {
    // The ranges are deliberately generous. Rejecting a real customer is a
    // worse failure than accepting an unusual measurement.
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 68,
      waist: 66,
      hip: 76,
      shoulder: 24,
      kameez_length: 55,
      sleeve_length: 26,
    });
    expect(result.success).toBe(true);
  });
});

describe("cross-field rules mirror the serializer", () => {
  it("rejects an underbust larger than the bust", () => {
    const result = fitProfileSchema("blouse").safeParse({
      bust: 34,
      underbust: 40,
      shoulder: 14,
      blouse_length: 15,
      sleeve_length: 6,
      armhole: 16,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message).join(" ")).toMatch(
        /Underbust cannot exceed bust/,
      );
    }
  });

  it("rejects a waist implausibly far from bust and hip", () => {
    const result = fitProfileSchema("suit_set").safeParse({
      bust: 34,
      waist: 68,
      hip: 36,
      shoulder: 15,
      kameez_length: 42,
      sleeve_length: 22,
    });
    expect(result.success).toBe(false);
  });

  it("reports the error on every participating field", () => {
    const result = fitProfileSchema("blouse").safeParse({
      bust: 34,
      underbust: 40,
      shoulder: 14,
      blouse_length: 15,
      sleeve_length: 6,
      armhole: 16,
    });
    if (!result.success) {
      const paths = result.error.issues.flatMap((i) => i.path);
      expect(paths).toContain("underbust");
      expect(paths).toContain("bust");
    }
  });

  it("skips a rule when its fields are absent", () => {
    // A rule must not fire on data it cannot evaluate.
    for (const rule of CROSS_FIELD_RULES) {
      expect(rule.applies({})).toBe(false);
    }
  });
});
