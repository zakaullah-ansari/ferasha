"use client";

import { useMemo, useState } from "react";

import { FitDrawer, type FitSelection } from "@/components/FitDrawer";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { GarmentType } from "@/lib/api/fit-schema";
import type { ProductDetail, ProductVariant } from "@/lib/api/types";
import { ATELIER } from "@/lib/brand";
import { formatINR } from "@/lib/format";
import { useCartStore } from "@/store/useCartStore";

/**
 * Client island on an otherwise server-rendered product page.
 *
 * Only this subtree ships JavaScript: the gallery, copy, modesty block and
 * price are all server-rendered, which is what keeps the product page inside
 * its client-JS budget.
 *
 * Colour + standard size resolve to exactly one variant, which is what goes in
 * the bag. Bespoke measurements cannot travel through the bag yet, so a
 * bespoke choice routes the customer to the atelier instead.
 */
/** Mirrors backend-core catalog.enums.SizeStandard, smallest first. */
const SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "FREE"];
const bySize = (a: string, b: string) => SIZE_ORDER.indexOf(a) - SIZE_ORDER.indexOf(b);

export function ProductPurchasePanel({ product }: { product: ProductDetail }) {
  const addItem = useCartStore((state) => state.addItem);
  const openBag = useCartStore((state) => state.setDrawerOpen);

  const purchasable = useMemo(
    () => product.variants.filter((v) => v.is_active && v.in_stock),
    [product.variants],
  );
  const colours = useMemo(() => [...new Set(purchasable.map((v) => v.colour))], [purchasable]);

  const [colour, setColour] = useState<string | undefined>(colours[0]);
  const [open, setOpen] = useState(false);
  const [selection, setSelection] = useState<FitSelection | null>(null);

  const sizes = purchasable
    .filter((v) => v.colour === colour)
    .map((v) => v.size)
    .sort(bySize);
  const variant: ProductVariant | undefined =
    selection?.mode === "standard"
      ? purchasable.find((v) => v.colour === colour && v.size === selection.size)
      : undefined;

  function chooseColour(next: string) {
    setColour(next);
    // The chosen size may not exist in the new colour; ask again.
    setSelection(null);
  }

  function addToBag() {
    if (!variant) return;
    addItem({
      variantId: variant.id,
      name: product.name,
      price: Number(variant.price),
      image: product.primary_image ?? "",
      colour: variant.colour,
      size: variant.size,
      quantity: 1,
    });
    openBag(true);
  }

  if (purchasable.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Currently made to order only. Call the atelier on{" "}
        <a href={ATELIER.phoneHref} className="underline underline-offset-4">
          {ATELIER.phoneDisplay}
        </a>
        .
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {colours.length > 1 && (
        <div className="space-y-2">
          <p id="colour-label" className="text-sm font-medium">
            Colour: <span className="font-normal text-muted-foreground">{colour}</span>
          </p>
          <ToggleGroup
            aria-labelledby="colour-label"
            variant="outline"
            value={colour ? [colour] : []}
            onValueChange={(value) => value[0] && chooseColour(value[0])}
            className="flex-wrap"
          >
            {colours.map((option) => (
              <ToggleGroupItem key={option} value={option}>
                {option}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button variant="outline" size="lg" className="flex-1" onClick={() => setOpen(true)}>
          {selection?.mode === "standard" ? `Size ${selection.size} · Change` : "Select your fit"}
        </Button>
        <Button size="lg" className="flex-1" onClick={addToBag} disabled={!variant}>
          {variant ? `Add to bag · ${formatINR(variant.price)}` : "Add to bag"}
        </Button>
      </div>

      {selection?.mode === "standard" && !variant && (
        <p role="status" className="text-sm text-destructive">
          Size {selection.size} is not available in {colour}. Please choose another size.
        </p>
      )}

      {selection?.mode === "bespoke" && (
        <div role="status" className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          Your measurements are saved. Bespoke pieces are confirmed personally by{" "}
          {ATELIER.name}: call{" "}
          <a href={ATELIER.phoneHref} className="font-medium underline underline-offset-4">
            {ATELIER.phoneDisplay}
          </a>{" "}
          to place this order. Stitching takes {product.stitching_days} days.
        </div>
      )}

      {product.supports_bespoke && (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Bespoke tailoring from {formatINR(product.base_price)} plus surcharge ·{" "}
          {product.stitching_days} days
        </p>
      )}

      <FitDrawer
        open={open}
        onClose={() => setOpen(false)}
        garment={product.garment_type as GarmentType}
        productName={product.name}
        supportsBespoke={product.supports_bespoke}
        sizes={sizes}
        onSubmit={setSelection}
      />
    </div>
  );
}
