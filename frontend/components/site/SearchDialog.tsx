"use client";

import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import type { ProductSummary } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

/** Words shoppers use for this catalogue; shown when a search finds nothing, and before typing. */
const SUGGESTIONS = ["Gharara", "Sharara", "Lehenga", "Chikankari", "Zardozi", "Lawn", "Velvet"] as const;
const MIN_LENGTH = 2;
const PREVIEW = 5;

type Results = { query: string; products: readonly ProductSummary[]; count: number };

const resultsHref = (query: string) => `/products?search=${encodeURIComponent(query.trim())}`;

/**
 * Header search: a few matches as you type, the full results on Enter.
 * Opens with "/" or Ctrl/⌘+K as well as the button.
 */
export function SearchDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const term = query.trim();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const typing = event.target instanceof HTMLElement && event.target.closest("input, textarea, [contenteditable]");
      if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
        event.preventDefault();
        setOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // A short pause after typing; a newer search cancels the one in flight.
  useEffect(() => {
    if (term.length < MIN_LENGTH) {
      setResults(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .listProducts({ search: term }, { signal: controller.signal })
        .then(({ results: products, count }) => setResults({ query: term, products: products.slice(0, PREVIEW), count }))
        .catch(() => undefined)
        .finally(() => !controller.signal.aborted && setLoading(false));
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [term]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (term.length === 0) return;
    setOpen(false);
    router.push(resultsHref(term));
  }

  const close = () => setOpen(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="ghost" size="icon" aria-label="Search" />}>
        <Search />
      </DialogTrigger>
      {/* No corner close button: it would sit on the search box's own clear button. Escape or a tap outside closes. */}
      <DialogContent showCloseButton={false} className="top-[12vh] translate-y-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Search the collection</DialogTitle>
        <DialogDescription className="sr-only">Type a garment, fabric or embellishment, then press Enter for every result.</DialogDescription>
        <form role="search" onSubmit={submit} className="relative">
          <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Gharara, chikankari, velvet…"
            aria-label="Search the collection"
            className="h-11 pl-9 text-base"
          />
        </form>

        <div aria-live="polite" aria-busy={loading} className="min-h-24">
          {term.length < MIN_LENGTH ? (
            <Suggestions onPick={setQuery} label="Popular searches" />
          ) : results && results.query === term ? (
            results.count === 0 ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">Nothing matches “{term}” yet. Try one of these:</p>
                <Suggestions onPick={setQuery} />
              </div>
            ) : (
              <div className="space-y-2">
                <ul className="divide-y">
                  {results.products.map((product) => (
                    <li key={product.id}>
                      <Link href={`/products/${product.slug}`} onClick={close} className="flex items-center gap-3 py-2.5 hover:text-primary">
                        <span className="size-12 shrink-0 overflow-hidden rounded-md bg-muted">
                          {product.primary_image && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={product.primary_image} alt="" className="size-full object-cover" />
                          )}
                        </span>
                        <span className="min-w-0 flex-1 truncate">{product.name}</span>
                        <span className="text-sm tabular-nums text-muted-foreground">{formatINR(product.base_price)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <Link
                  href={resultsHref(term)}
                  onClick={close}
                  className="flex items-center justify-between rounded-xl bg-muted px-3 py-2.5 text-sm font-medium hover:text-primary"
                >
                  See all {results.count} {results.count === 1 ? "result" : "results"} for “{term}”
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Link>
              </div>
            )
          ) : (
            <p className="text-sm text-muted-foreground">Searching…</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Suggestions({ onPick, label }: { onPick: (term: string) => void; label?: string }) {
  return (
    <div>
      {label && <p className="mb-2 text-xs tracking-[0.2em] text-muted-foreground uppercase">{label}</p>}
      <ul className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((term) => (
          <li key={term}>
            <Button type="button" variant="secondary" size="sm" onClick={() => onPick(term)}>
              {term}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
