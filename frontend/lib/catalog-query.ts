/**
 * The collection page's state, which lives in the URL.
 *
 * A filtered view is a link: it survives a reload, can be shared on WhatsApp
 * and is rendered on the server. Everything here is pure - parse the query
 * string, change one thing, serialise it back - so the panel, the chips, the
 * sort menu and the pagination all agree on what a selection means.
 *
 * Keys and values mirror backend-core catalog/filters.py.
 */

import type { FacetOption, Facets } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

/** Multi-value facets: options within one are OR-ed, facets are AND-ed. */
export const FACET_KEYS = ["occasion", "garment_type", "fabric", "work_type"] as const;
export type FacetKey = (typeof FACET_KEYS)[number];

/** On/off switches, sent as `key=true`. The modesty five come first in the panel. */
export const MODESTY_KEYS = [
  "fully_covered",
  "has_full_lining",
  "is_opaque",
  "full_sleeves",
  "no_slit",
] as const;
const FLAG_KEYS = [...MODESTY_KEYS, "supports_bespoke"] as const;
export type FlagKey = (typeof FLAG_KEYS)[number];

export const SORTS = [
  { value: "-created", label: "Newest" },
  { value: "price", label: "Price: low to high" },
  { value: "-price", label: "Price: high to low" },
] as const;
export type SortValue = (typeof SORTS)[number]["value"];
/** The API's own default (Product.Meta.ordering), so the URL can omit it. */
const DEFAULT_SORT: SortValue = "-created";

export interface PricePreset {
  readonly id: string;
  readonly label: string;
  readonly min?: string;
  readonly max?: string;
}

/** Bands that split the current catalogue (₹1,890 to ₹1,89,000) usefully. */
export const PRICE_PRESETS: readonly PricePreset[] = [
  { id: "under-5k", label: "Under ₹5,000", max: "5000" },
  { id: "5k-25k", label: "₹5,000 – ₹25,000", min: "5000", max: "25000" },
  { id: "25k-1l", label: "₹25,000 – ₹1,00,000", min: "25000", max: "100000" },
  { id: "over-1l", label: "Over ₹1,00,000", min: "100000" },
];

export interface CatalogQuery {
  /** The collection being browsed; context for the heading, not a filter chip. */
  readonly category?: string;
  readonly search?: string;
  readonly facets: Readonly<Record<FacetKey, readonly string[]>>;
  readonly flags: readonly FlagKey[];
  readonly priceMin?: string;
  readonly priceMax?: string;
  readonly ordering: SortValue;
  readonly page: number;
}

/** What Next hands a page as `searchParams`. */
export type RawSearchParams = Readonly<Record<string, string | readonly string[] | undefined>>;

const EMPTY_FACETS: CatalogQuery["facets"] = { occasion: [], garment_type: [], fabric: [], work_type: [] };

const all = (value: string | readonly string[] | undefined): readonly string[] =>
  value === undefined ? [] : typeof value === "string" ? [value] : value;

const first = (value: string | readonly string[] | undefined): string | undefined =>
  all(value).find((item) => item.trim() !== "")?.trim();

/** A price bound the API will accept: digits, optionally with paise. */
const price = (value: string | readonly string[] | undefined): string | undefined => {
  const bound = first(value);
  return bound && /^\d+(\.\d{1,2})?$/.test(bound) ? bound : undefined;
};

/**
 * Read a query string into a selection. Unknown keys are dropped rather than
 * forwarded, so the API (and its cache) only ever sees parameters it knows.
 */
export function parseCatalogQuery(params: RawSearchParams): CatalogQuery {
  const facets = Object.fromEntries(
    FACET_KEYS.map((key) => [key, [...new Set(all(params[key]).filter(Boolean))]]),
  ) as unknown as CatalogQuery["facets"];
  const ordering = SORTS.find((sort) => sort.value === first(params.ordering))?.value ?? DEFAULT_SORT;
  const page = Number.parseInt(first(params.page) ?? "", 10);

  return {
    category: first(params.category),
    search: first(params.search),
    facets,
    flags: FLAG_KEYS.filter((key) => first(params[key]) === "true"),
    priceMin: price(params.price_min),
    priceMax: price(params.price_max),
    ordering,
    page: Number.isSafeInteger(page) && page > 1 ? page : 1,
  };
}

/** The filters alone: what the facet counts are computed for. */
export function filterParams(query: CatalogQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.category) params.set("category", query.category);
  if (query.search) params.set("search", query.search);
  for (const key of FACET_KEYS) for (const value of query.facets[key]) params.append(key, value);
  for (const flag of query.flags) params.set(flag, "true");
  if (query.priceMin) params.set("price_min", query.priceMin);
  if (query.priceMax) params.set("price_max", query.priceMax);
  return params;
}

/** The canonical query string: defaults are left out, so one view has one URL. */
export function toSearchParams(query: CatalogQuery): URLSearchParams {
  const params = filterParams(query);
  if (query.ordering !== DEFAULT_SORT) params.set("ordering", query.ordering);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

export function toHref(pathname: string, query: CatalogQuery): string {
  const search = toSearchParams(query).toString();
  return search ? `${pathname}?${search}` : pathname;
}

/* Changes. Each returns a new selection; any change of filter or order goes back to page one. */

export function toggleFacet(query: CatalogQuery, key: FacetKey, value: string): CatalogQuery {
  const current = query.facets[key];
  const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
  return { ...query, facets: { ...query.facets, [key]: next }, page: 1 };
}

export function toggleFlag(query: CatalogQuery, flag: FlagKey): CatalogQuery {
  const flags = query.flags.includes(flag)
    ? query.flags.filter((item) => item !== flag)
    : FLAG_KEYS.filter((key) => key === flag || query.flags.includes(key));
  return { ...query, flags, page: 1 };
}

/** `null` clears the price band. */
export function withPrice(query: CatalogQuery, preset: PricePreset | null): CatalogQuery {
  return { ...query, priceMin: preset?.min, priceMax: preset?.max, page: 1 };
}

export function withOrdering(query: CatalogQuery, ordering: SortValue): CatalogQuery {
  return { ...query, ordering, page: 1 };
}

export function withPage(query: CatalogQuery, page: number): CatalogQuery {
  return { ...query, page };
}

export function withoutSearch(query: CatalogQuery): CatalogQuery {
  return { ...query, search: undefined, page: 1 };
}

/** Everything the shopper chose, keeping the collection they are in and their sort. */
export function clearFilters(query: CatalogQuery): CatalogQuery {
  return { category: query.category, facets: EMPTY_FACETS, flags: [], ordering: query.ordering, page: 1 };
}

export function activePreset(query: CatalogQuery): PricePreset | undefined {
  return PRICE_PRESETS.find((preset) => preset.min === query.priceMin && preset.max === query.priceMax);
}

/* Presentation. */

/** "raw_silk" -> "Raw silk", for a value the facet counts do not label. */
const humanise = (value: string) => {
  const words = value.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
};

const FLAG_LABELS: Record<FlagKey, string> = {
  fully_covered: "Fully covered",
  has_full_lining: "Fully lined",
  is_opaque: "Opaque fabric",
  full_sleeves: "Full sleeves",
  no_slit: "No slit",
  supports_bespoke: "Bespoke available",
};

/**
 * A facet's options for the panel. The counts only list values with garments,
 * so a value the shopper picked that other filters have since emptied would
 * vanish and could not be unticked; it is kept, at zero.
 */
export function facetOptions(query: CatalogQuery, facets: Facets, key: FacetKey): FacetOption[] {
  const listed = facets[key];
  const missing = query.facets[key]
    .filter((value) => !listed.some((option) => option.value === value))
    .map((value) => ({ value, label: humanise(value), count: 0 }));
  return [...listed, ...missing];
}

export function flagLabel(flag: FlagKey, facets?: Facets): string {
  return facets?.modesty.find((option) => option.value === flag)?.label ?? FLAG_LABELS[flag];
}

export interface ActiveFilter {
  readonly id: string;
  readonly label: string;
  /** The selection with this one filter removed. */
  readonly without: CatalogQuery;
}

/** One chip per choice the shopper made, labelled the way the panel labels it. */
export function activeFilters(query: CatalogQuery, facets?: Facets): ActiveFilter[] {
  const chips: ActiveFilter[] = [];
  if (query.search) {
    chips.push({ id: "search", label: `“${query.search}”`, without: withoutSearch(query) });
  }
  for (const flag of query.flags) {
    chips.push({ id: flag, label: flagLabel(flag, facets), without: toggleFlag(query, flag) });
  }
  for (const key of FACET_KEYS) {
    for (const value of query.facets[key]) {
      const label = facets?.[key].find((option) => option.value === value)?.label ?? humanise(value);
      chips.push({ id: `${key}:${value}`, label, without: toggleFacet(query, key, value) });
    }
  }
  if (query.priceMin || query.priceMax) {
    const label =
      activePreset(query)?.label ??
      [query.priceMin && `From ${formatINR(query.priceMin)}`, query.priceMax && `up to ${formatINR(query.priceMax)}`]
        .filter(Boolean)
        .join(" ");
    chips.push({ id: "price", label, without: withPrice(query, null) });
  }
  return chips;
}

/**
 * The heading for a selection: the collection's name, else the one occasion
 * chosen, else the search, else the whole collection.
 */
export function collectionTitle(query: CatalogQuery, categoryName?: string, facets?: Facets): string {
  if (categoryName) return categoryName;
  const [occasion, ...more] = query.facets.occasion;
  if (occasion && more.length === 0) {
    return facets?.occasion.find((option) => option.value === occasion)?.label ?? humanise(occasion);
  }
  if (query.search) return `Results for “${query.search}”`;
  return "The collection";
}
