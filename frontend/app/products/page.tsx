import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CollectionView } from "@/components/catalog/CollectionView";
import { ApiError, api } from "@/lib/api/client";
import {
  type CatalogQuery,
  clearFilters,
  collectionTitle,
  filterParams,
  parseCatalogQuery,
  type RawSearchParams,
  toHref,
  toSearchParams,
  withPage,
} from "@/lib/catalog-query";

export const revalidate = 60;

const PATH = "/products";

type Props = { searchParams: Promise<RawSearchParams> };

/** The collection's name for the heading. A missing one is not an error: the grid will say it is empty. */
async function categoryFor(query: CatalogQuery) {
  if (!query.category) return null;
  try {
    return await api.getCategory(query.category);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const query = parseCatalogQuery(await searchParams);
  return { title: collectionTitle(query, (await categoryFor(query))?.name) };
}

export default async function ProductsPage({ searchParams }: Props) {
  const query = parseCatalogQuery(await searchParams);

  let data;
  try {
    data = await Promise.all([
      api.listProducts(toSearchParams(query)),
      api.getFacets(filterParams(query)),
      categoryFor(query),
    ]);
  } catch (error) {
    // Old links outlive the catalogue: a page past the end, or a filter value
    // that no longer exists. Land on the nearest view that does.
    if (error instanceof ApiError && error.status === 404 && query.page > 1) data = toHref(PATH, withPage(query, 1));
    else if (error instanceof ApiError && error.status === 400) data = toHref(PATH, clearFilters(query));
    else throw error;
  }
  // Outside the try: redirect() works by throwing.
  if (typeof data === "string") redirect(data);

  const [{ results, count }, facets, category] = data;
  return <CollectionView query={query} facets={facets} products={results} count={count} category={category} />;
}
