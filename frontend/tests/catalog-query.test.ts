import { describe, expect, it } from "vitest";

import {
  activeFilters,
  activePreset,
  clearFilters,
  collectionTitle,
  facetOptions,
  pageWindow,
  parseCatalogQuery,
  PRICE_PRESETS,
  toggleFacet,
  toggleFlag,
  toHref,
  toSearchParams,
  withOrdering,
  withPage,
  withPrice,
} from "@/lib/catalog-query";

import { FACETS } from "./fixtures/commerce";

describe("parseCatalogQuery", () => {
  it("keeps every value of a repeated key, once", () => {
    const query = parseCatalogQuery({ occasion: ["eid", "nikah", "eid"] });
    expect(query.facets.occasion).toEqual(["eid", "nikah"]);
  });

  it("drops keys the API does not know", () => {
    const query = parseCatalogQuery({ utm_source: "whatsapp", fabric: "lawn" });
    expect(toSearchParams(query).toString()).toBe("fabric=lawn");
  });

  it("treats a switch as on only when it is exactly true", () => {
    const query = parseCatalogQuery({ fully_covered: "true", no_slit: "1", is_opaque: "false" });
    expect(query.flags).toEqual(["fully_covered"]);
  });

  it("falls back to safe defaults for bad sort, page and price values", () => {
    const query = parseCatalogQuery({ ordering: "stock_quantity", page: "-3", price_min: "1e9", price_max: "5000" });
    expect(query).toMatchObject({ ordering: "-created", page: 1, priceMin: undefined, priceMax: "5000" });
  });
});

describe("toSearchParams", () => {
  it("round-trips a selection through the URL", () => {
    const raw = {
      category: "bridal",
      occasion: ["nikah", "eid"],
      fully_covered: "true",
      price_min: "5000",
      price_max: "25000",
      ordering: "price",
      page: "2",
    };
    const query = parseCatalogQuery(raw);
    const again = parseCatalogQuery(Object.fromEntries(
      [...new Set(toSearchParams(query).keys())].map((key) => [key, toSearchParams(query).getAll(key)]),
    ));
    expect(again).toEqual(query);
  });

  it("leaves defaults out, so one view has one URL", () => {
    const query = parseCatalogQuery({ ordering: "-created", page: "1" });
    expect(toHref("/products", query)).toBe("/products");
  });
});

describe("changing the selection", () => {
  const base = parseCatalogQuery({ category: "suits", occasion: "eid", ordering: "price", page: "3" });

  it("adds and removes a facet value, back on page one", () => {
    const added = toggleFacet(base, "occasion", "nikah");
    expect(added.facets.occasion).toEqual(["eid", "nikah"]);
    expect(added.page).toBe(1);
    expect(toggleFacet(added, "occasion", "eid").facets.occasion).toEqual(["nikah"]);
  });

  it("keeps switches in panel order whatever order they were picked in", () => {
    const query = toggleFlag(toggleFlag(base, "no_slit"), "fully_covered");
    expect(query.flags).toEqual(["fully_covered", "no_slit"]);
    expect(toggleFlag(query, "no_slit").flags).toEqual(["fully_covered"]);
  });

  it("sets and clears a price band", () => {
    const band = PRICE_PRESETS[1]!;
    const priced = withPrice(base, band);
    expect(activePreset(priced)).toBe(band);
    expect(withPrice(priced, null)).toMatchObject({ priceMin: undefined, priceMax: undefined });
  });

  it("goes back to page one on a new sort, but not on a page change", () => {
    expect(withOrdering(base, "-price").page).toBe(1);
    expect(withPage(base, 4).page).toBe(4);
  });

  it("clears the filters but keeps the collection and the sort", () => {
    const cleared = clearFilters(toggleFlag(base, "fully_covered"));
    expect(toSearchParams(cleared).toString()).toBe("category=suits&ordering=price");
  });
});

describe("activeFilters", () => {
  it("labels each chip as the panel does, and each removes only itself", () => {
    const query = parseCatalogQuery({
      category: "bridal",
      search: "gharara",
      occasion: ["nikah", "walima"],
      fabric: "raw_silk",
      fully_covered: "true",
      price_min: "100000",
    });
    const chips = activeFilters(query, FACETS);

    expect(chips.map((chip) => chip.label)).toEqual([
      "“gharara”", "Fully covered", "Nikah", "Walima", "Raw silk", "Over ₹1,00,000",
    ]);
    const nikah = chips.find((chip) => chip.id === "occasion:nikah")!;
    expect(nikah.without.facets.occasion).toEqual(["walima"]);
    expect(nikah.without.category).toBe("bridal");
  });

  it("names values the counts do not include, and odd price ranges", () => {
    const query = parseCatalogQuery({ fabric: "raw_silk", price_min: "3000", price_max: "9000" });
    expect(activeFilters(query).map((chip) => chip.label)).toEqual(["Raw silk", "From ₹3,000 up to ₹9,000"]);
  });

  it("never makes a chip for the collection itself", () => {
    expect(activeFilters(parseCatalogQuery({ category: "bridal" }))).toEqual([]);
  });
});

describe("collectionTitle", () => {
  it("prefers the collection, then a single occasion, then the search", () => {
    expect(collectionTitle(parseCatalogQuery({ occasion: "eid" }), "Bridal", FACETS)).toBe("Bridal");
    expect(collectionTitle(parseCatalogQuery({ occasion: "casual" }), undefined, FACETS)).toBe("Casual / Daily");
    expect(collectionTitle(parseCatalogQuery({ occasion: ["eid", "nikah"], search: "silk" }))).toBe("Results for “silk”");
    expect(collectionTitle(parseCatalogQuery({}))).toBe("The collection");
  });
});

describe("pageWindow", () => {
  it.each([
    [1, 1, [1]],
    [1, 3, [1, 2, 3]],
    [1, 10, [1, 2, "gap", 10]],
    [5, 10, [1, "gap", 4, 5, 6, "gap", 10]],
    [3, 10, [1, 2, 3, 4, "gap", 10]],
    [10, 10, [1, "gap", 9, 10]],
  ])("page %i of %i", (current, total, expected) => {
    expect(pageWindow(current, total)).toEqual(expected);
  });
});

describe("facetOptions", () => {
  it("keeps a picked value the other filters have emptied, so it can be unticked", () => {
    const query = parseCatalogQuery({ occasion: ["eid", "mehndi_night"] });
    const options = facetOptions(query, FACETS, "occasion");
    expect(options.at(-1)).toEqual({ value: "mehndi_night", label: "Mehndi night", count: 0 });
    expect(options.filter((option) => option.value === "eid")).toHaveLength(1);
  });
});
