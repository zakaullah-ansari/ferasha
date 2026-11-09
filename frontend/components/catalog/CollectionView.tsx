import Link from "next/link";

import { ProductCard } from "@/components/ProductCard";
import { BlurFade } from "@/components/ui/blur-fade";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import type { Category, Facets, ProductSummary } from "@/lib/api/types";
import { type CatalogQuery, collectionTitle } from "@/lib/catalog-query";
import { pageCount } from "@/lib/pagination";

import { ActiveFilters, CatalogPagination, SortSelect } from "./CatalogControls";
import { CatalogNavigation } from "./CatalogNavigation";
import { CatalogResults, EmptyCollection } from "./CatalogResults";
import { FilterPanel, MobileFilters } from "./FilterPanel";

interface CollectionViewProps {
  readonly query: CatalogQuery;
  readonly facets: Facets;
  readonly products: readonly ProductSummary[];
  readonly count: number;
  readonly category?: Category | null;
}

/** The collection page, given its data. The route loads it; stories pass fixtures. */
export function CollectionView({ query, facets, products, count, category }: CollectionViewProps) {
  const title = collectionTitle(query, category?.name, facets);

  return (
    <CatalogNavigation query={query}>
      <div className="mx-auto max-w-7xl px-5 pt-6 pb-24">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink render={<Link href="/" />}>Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            {category ? (
              <>
                <BreadcrumbItem>
                  <BreadcrumbLink render={<Link href="/products" />}>Collection</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>{category.name}</BreadcrumbPage>
                </BreadcrumbItem>
              </>
            ) : (
              <BreadcrumbItem>
                <BreadcrumbPage>Collection</BreadcrumbPage>
              </BreadcrumbItem>
            )}
          </BreadcrumbList>
        </Breadcrumb>

        <header className="mt-10 max-w-2xl">
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">Ferasha, by Kausar</p>
          <h1 className="mt-3 font-display text-display-sm leading-tight">{title}</h1>
          {category?.description && (
            <p className="mt-4 leading-relaxed text-muted-foreground">{category.description}</p>
          )}
        </header>

        <div className="mt-10 lg:grid lg:grid-cols-[15rem_1fr] lg:gap-12">
          <aside
            aria-label="Filters"
            className="hidden lg:sticky lg:top-24 lg:block lg:max-h-[calc(100svh-7rem)] lg:self-start lg:overflow-y-auto"
          >
            <FilterPanel facets={facets} />
          </aside>

          <div>
            <div className="flex items-center justify-between gap-4 border-b pb-4">
              <div className="flex items-center gap-3">
                <MobileFilters facets={facets} />
                <p aria-live="polite" className="text-sm text-muted-foreground">
                  {count} {count === 1 ? "garment" : "garments"}
                </p>
              </div>
              <SortSelect />
            </div>

            <ActiveFilters facets={facets} className="mt-4" />

            <CatalogResults>
              {products.length === 0 ? (
                <EmptyCollection />
              ) : (
                <ul className="mt-8 grid grid-cols-2 gap-x-5 gap-y-12 xl:grid-cols-3">
                  {products.map((product, index) => (
                    <li key={product.id}>
                      {/* A short stagger for the first row or two; later cards are below the fold. */}
                      <BlurFade delay={Math.min(index, 6) * 0.05}>
                        <ProductCard product={product} />
                      </BlurFade>
                    </li>
                  ))}
                </ul>
              )}
            </CatalogResults>

            <CatalogPagination pageCount={pageCount(count)} className="mt-16" />
          </div>
        </div>
      </div>
    </CatalogNavigation>
  );
}
