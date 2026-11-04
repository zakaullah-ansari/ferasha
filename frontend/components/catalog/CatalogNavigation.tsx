"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useOptimistic, useTransition } from "react";

import { type CatalogQuery, toHref } from "@/lib/catalog-query";

interface CatalogNavigationValue {
  /** The selection on screen: the shopper's latest change, before the server has answered. */
  readonly query: CatalogQuery;
  /** True while the new results render; the grid dims rather than blanking. */
  readonly isPending: boolean;
  readonly href: (next: CatalogQuery) => string;
  readonly navigate: (next: CatalogQuery, options?: { scroll?: boolean }) => void;
}

const Context = createContext<CatalogNavigationValue | null>(null);

/**
 * Moves the collection page between selections.
 *
 * The URL is the state and the server renders it. A tick shows at once
 * (optimistic) while the transition keeps the current garments on screen
 * until the new ones are ready, instead of flashing a loading state per
 * click. Filtering keeps the scroll position; paging returns to the top.
 */
export function CatalogNavigation({ query, children }: { query: CatalogQuery; children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [optimistic, setOptimistic] = useOptimistic(query);

  const href = (next: CatalogQuery) => toHref(pathname, next);
  const navigate = (next: CatalogQuery, { scroll = false } = {}) =>
    startTransition(() => {
      setOptimistic(next);
      router.push(href(next), { scroll });
    });

  return <Context value={{ query: optimistic, isPending, href, navigate }}>{children}</Context>;
}

export function useCatalogNavigation(): CatalogNavigationValue {
  const value = useContext(Context);
  if (!value) throw new Error("useCatalogNavigation must be used inside <CatalogNavigation>.");
  return value;
}
