"use client";

import { SlidersHorizontal } from "lucide-react";
import { useId, useState } from "react";

import { ResponsivePanel } from "@/components/ResponsivePanel";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { FacetOption, Facets } from "@/lib/api/types";
import {
  activeFilters,
  activePreset,
  type FacetKey,
  facetOptions,
  type FlagKey,
  PRICE_PRESETS,
  toggleFacet,
  toggleFlag,
  withPrice,
} from "@/lib/catalog-query";

import { useCatalogNavigation } from "./CatalogNavigation";

const SECTIONS: readonly { key: FacetKey; title: string }[] = [
  { key: "occasion", title: "Occasion" },
  { key: "garment_type", title: "Garment" },
  { key: "fabric", title: "Fabric" },
  { key: "work_type", title: "Embellishment" },
];

function Option({
  id,
  option,
  checked,
  onToggle,
}: {
  id: string;
  option: FacetOption;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <li className="flex items-center gap-3 py-1.5">
      {/* A choice that would empty the page is shown but cannot be picked; one already picked can always be undone. */}
      <Checkbox id={id} checked={checked} onCheckedChange={onToggle} disabled={!checked && option.count === 0} />
      <Label htmlFor={id} className="flex-1 font-normal">
        {option.label}
      </Label>
      <span className="text-xs text-muted-foreground tabular-nums">{option.count}</span>
    </li>
  );
}

/** One collapsible group, titled in the site's small-caps eyebrow style, with how many are chosen. */
function Section({
  value,
  title,
  selected,
  children,
}: {
  value: string;
  title: string;
  selected: number;
  children: React.ReactNode;
}) {
  return (
    <AccordionItem value={value} className="data-open:bg-transparent">
      <AccordionTrigger className="px-0 font-sans text-xs tracking-[0.2em] uppercase">
        <span>
          {title}
          {selected > 0 && <span className="ml-2 text-primary tabular-nums">{selected}</span>}
        </span>
      </AccordionTrigger>
      <AccordionContent className="px-0">{children}</AccordionContent>
    </AccordionItem>
  );
}

/**
 * Filters with live counts. Modesty comes first: it is what this catalogue
 * can promise that others cannot, and every garment is labelled, so the
 * counts are exact.
 */
export function FilterPanel({ facets }: { facets: Facets }) {
  const { query, navigate } = useCatalogNavigation();
  // The panel is mounted twice (sidebar and phone sheet); ids must not collide.
  const id = useId();
  const flag = (key: FlagKey) => ({
    checked: query.flags.includes(key),
    onToggle: () => navigate(toggleFlag(query, key)),
  });
  const modestyCount = query.flags.filter((key) => key !== "supports_bespoke").length;
  const price = activePreset(query)?.id ?? (query.priceMin || query.priceMax ? "custom" : "any");

  return (
    // Unframed: in a sidebar or a sheet the sections need rules between them, not a card around them.
    <Accordion multiple defaultValue={["modesty", "occasion", "price"]} className="rounded-none border-0">
      <Section value="modesty" title="Modesty" selected={modestyCount}>
        <ul>
          {facets.modesty.map((option) => (
            <Option key={option.value} id={`${id}-${option.value}`} option={option} {...flag(option.value as FlagKey)} />
          ))}
        </ul>
      </Section>

      {SECTIONS.map(({ key, title }) => ({ key, title, options: facetOptions(query, facets, key) }))
        .filter(({ options }) => options.length > 0)
        .map(({ key, title, options }) => (
        <Section key={key} value={key} title={title} selected={query.facets[key].length}>
          <ul>
            {options.map((option) => (
              <Option
                key={option.value}
                id={`${id}-${key}-${option.value}`}
                option={option}
                checked={query.facets[key].includes(option.value)}
                onToggle={() => navigate(toggleFacet(query, key, option.value))}
              />
            ))}
          </ul>
        </Section>
      ))}

      <Section value="bespoke" title="Made for you" selected={query.flags.includes("supports_bespoke") ? 1 : 0}>
        <ul>
          <Option
            id={`${id}-bespoke`}
            option={{ value: "supports_bespoke", label: "Bespoke available", count: facets.supports_bespoke }}
            {...flag("supports_bespoke")}
          />
        </ul>
      </Section>

      <Section value="price" title="Price" selected={price === "any" ? 0 : 1}>
        <RadioGroup
          aria-label="Price"
          value={price}
          onValueChange={(value) =>
            navigate(withPrice(query, PRICE_PRESETS.find((preset) => preset.id === value) ?? null))
          }
          className="gap-0"
        >
          {[{ id: "any", label: "Any price" }, ...PRICE_PRESETS].map((preset) => (
            <div key={preset.id} className="flex items-center gap-3 py-1.5">
              <RadioGroupItem id={`${id}-price-${preset.id}`} value={preset.id} />
              <Label htmlFor={`${id}-price-${preset.id}`} className="font-normal">
                {preset.label}
              </Label>
            </div>
          ))}
        </RadioGroup>
      </Section>
    </Accordion>
  );
}

/** Phones and tablets: the same panel in a sheet, closed by a button that says what it will show. */
export function MobileFilters({ facets }: { facets: Facets }) {
  const { query, isPending } = useCatalogNavigation();
  const [open, setOpen] = useState(false);
  const active = activeFilters(query, facets).length;

  return (
    <>
      <Button variant="outline" className="lg:hidden" onClick={() => setOpen(true)}>
        <SlidersHorizontal data-icon="inline-start" />
        Filters
        {active > 0 && <Badge aria-label={`${active} active`}>{active}</Badge>}
      </Button>
      <ResponsivePanel
        open={open}
        onOpenChange={setOpen}
        title="Filters"
        footer={
          <Button size="lg" className="w-full" onClick={() => setOpen(false)}>
            {isPending ? "Updating…" : `Show ${facets.total} ${facets.total === 1 ? "garment" : "garments"}`}
          </Button>
        }
      >
        <FilterPanel facets={facets} />
      </ResponsivePanel>
    </>
  );
}
