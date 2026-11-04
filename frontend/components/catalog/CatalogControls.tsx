"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Facets } from "@/lib/api/types";
import { activeFilters, clearFilters, pageWindow, SORTS, withOrdering, withPage } from "@/lib/catalog-query";
import { cn } from "@/lib/cn";

import { useCatalogNavigation } from "./CatalogNavigation";

export function SortSelect() {
  const { query, navigate } = useCatalogNavigation();
  return (
    <Select
      items={SORTS}
      value={query.ordering}
      onValueChange={(ordering) => ordering && navigate(withOrdering(query, ordering))}
    >
      <SelectTrigger aria-label="Sort by" className="min-w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {SORTS.map((sort) => (
          <SelectItem key={sort.value} value={sort.value}>
            {sort.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** What is narrowing the page, each removable on its own. */
export function ActiveFilters({ facets, className }: { facets: Facets; className?: string }) {
  const { query, navigate } = useCatalogNavigation();
  const chips = activeFilters(query, facets);
  if (chips.length === 0) return null;

  return (
    <ul aria-label="Active filters" className={cn("flex flex-wrap items-center gap-2", className)}>
      {chips.map((chip) => (
        <li key={chip.id}>
          <Button variant="secondary" size="sm" aria-label={`Remove filter: ${chip.label}`} onClick={() => navigate(chip.without)}>
            {chip.label}
            <X data-icon="inline-end" />
          </Button>
        </li>
      ))}
      {chips.length > 1 && (
        <li>
          <Button variant="link" size="sm" onClick={() => navigate(clearFilters(query))}>
            Clear all
          </Button>
        </li>
      )}
    </ul>
  );
}

/**
 * Real links, so pages are crawlable and open in a new tab; a plain click
 * moves within the app and returns to the top of the grid.
 */
export function CatalogPagination({ pageCount, className }: { pageCount: number; className?: string }) {
  const { query, href, navigate } = useCatalogNavigation();
  if (pageCount <= 1) return null;

  const to = (page: number) => ({
    href: href(withPage(query, page)),
    onClick: (event: React.MouseEvent<HTMLAnchorElement>) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      navigate(withPage(query, page), { scroll: true });
    },
  });

  return (
    <Pagination className={className}>
      <PaginationContent>
        {query.page > 1 && (
          <PaginationItem>
            <PaginationPrevious {...to(query.page - 1)} />
          </PaginationItem>
        )}
        {pageWindow(query.page, pageCount).map((item, index) =>
          item === "gap" ? (
            <PaginationItem key={`gap-${index}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={item}>
              <PaginationLink isActive={item === query.page} {...to(item)}>
                {item}
              </PaginationLink>
            </PaginationItem>
          ),
        )}
        {query.page < pageCount && (
          <PaginationItem>
            <PaginationNext {...to(query.page + 1)} />
          </PaginationItem>
        )}
      </PaginationContent>
    </Pagination>
  );
}
