"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ATELIER } from "@/lib/brand";
import { activeFilters, clearFilters } from "@/lib/catalog-query";
import { cn } from "@/lib/cn";

import { useCatalogNavigation } from "./CatalogNavigation";

/** The garments on screen, dimmed (not blanked) while the next selection renders. */
export function CatalogResults({ children }: { children: React.ReactNode }) {
  const { isPending } = useCatalogNavigation();
  return (
    <div aria-busy={isPending} className={cn("transition-opacity duration-300 ease-luxury", isPending && "opacity-50")}>
      {children}
    </div>
  );
}

/** No match is a prompt, not a dead end: loosen the filters, or have it made. */
export function EmptyCollection() {
  const { query, navigate } = useCatalogNavigation();
  const filtered = activeFilters(query).length > 0;

  return (
    <div className="flex flex-col items-center py-24 text-center">
      <p className="font-display text-3xl">Nothing matches all of these yet</p>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
        Loosen a filter, or have it made: {ATELIER.name} tailors to your measurements and to the coverage you want.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {filtered ? (
          <Button size="lg" onClick={() => navigate(clearFilters(query))}>
            Clear filters
          </Button>
        ) : (
          <Button size="lg" nativeButton={false} render={<Link href="/products" />}>
            See the whole collection
          </Button>
        )}
        <Button size="lg" variant="outline" nativeButton={false} render={<a href={ATELIER.phoneHref} />}>
          Call the atelier
        </Button>
      </div>
    </div>
  );
}
