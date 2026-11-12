"use client";

import { useState } from "react";

import { ProductCarousel, RailHeading, railHeadingId, ViewAllLink } from "@/components/product/ProductRail";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ProductSummary } from "@/lib/api/types";

export interface ProductTab {
  readonly label: string;
  /** Where "View all" goes while this tab is open. */
  readonly href: string;
  readonly products: readonly ProductSummary[];
  /** "View all" wording for this tab; defaults to "View all <label>". */
  readonly viewAllLabel?: string;
}

/**
 * A product rail with one tab per category, after the reference stores'
 * homepage grids. Every tab's products arrive with the page (fetched on the
 * server), so switching is instant and never shows a spinner. Empty tabs are
 * dropped rather than shown as dead ends; with one tab left it is a plain rail.
 */
export function TabbedProductRail({
  eyebrow,
  title,
  tabs,
}: {
  readonly eyebrow: string;
  readonly title: string;
  readonly tabs: readonly ProductTab[];
}) {
  const stocked = tabs.filter((tab) => tab.products.length > 0);
  const [active, setActive] = useState(0);
  const current = stocked[Math.min(active, stocked.length - 1)];
  if (!current) return null;

  const headingId = railHeadingId(eyebrow);

  return (
    <section aria-labelledby={headingId} className="mx-auto max-w-6xl px-5 py-16">
      <RailHeading eyebrow={eyebrow} title={title} headingId={headingId}>
        <ViewAllLink href={current.href} label={current.viewAllLabel ?? `View all ${current.label.toLowerCase()}`} />
      </RailHeading>

      {stocked.length === 1 ? (
        <ProductCarousel products={current.products} label={title} className="mt-10" />
      ) : (
        <Tabs value={active} onValueChange={(value) => setActive(Number(value))} className="mt-8">
          {/* Scrolls sideways on a phone rather than wrapping or squashing the labels. */}
          <div className="-mx-5 overflow-x-auto px-5">
            <TabsList variant="line" aria-label={`${title}: choose a category`}>
              {stocked.map((tab, index) => (
                <TabsTrigger key={tab.label} value={index} className="px-3">
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          {stocked.map((tab, index) => (
            <TabsContent key={tab.label} value={index} className="mt-6">
              <ProductCarousel products={tab.products} label={`${title}: ${tab.label}`} />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </section>
  );
}
