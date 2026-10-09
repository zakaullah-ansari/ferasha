"use client";

import { useState } from "react";

import { FitDrawer, type FitSelection } from "@/components/FitDrawer";
import type { GarmentType } from "@/lib/api/fit-schema";
import type { ProductDetail } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

/**
 * Client island on an otherwise server-rendered product page.
 *
 * Only this subtree ships JavaScript: the gallery, copy, modesty block and
 * price are all server-rendered, which is what keeps the product page inside
 * its client-JS budget.
 */
export function ProductPurchasePanel({ product }: { product: ProductDetail }) {
  const [open, setOpen] = useState(false);
  const [selection, setSelection] = useState<FitSelection | null>(null);

  const inStock = product.variants.filter((v) => v.in_stock && v.is_active);
  const available = inStock.length > 0;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="min-h-12 flex-1 rounded-full bg-ink-900 px-7 text-sm tracking-wide text-ivory hover:bg-ink-800"
        >
          Select your fit
        </button>
      </div>

      {/*
        Availability is a boolean, never a count. The API deliberately does
        not expose stock_quantity, so "only 2 left" is not something this
        storefront can render — scarcity theatre would require leaking
        inventory depth to competitors.
      */}
      <p className="mt-3 text-xs text-ink-600">
        {available
          ? `${inStock.length} of ${product.variants.length} options available`
          : "Currently made to order only"}
      </p>

      {selection && (
        <div
          role="status"
          className="mt-4 rounded-lg border border-gold-300 bg-gold-50 px-4 py-3 text-sm text-ink-800"
        >
          {selection.mode === "standard" ? (
            <>Size <strong>{selection.size}</strong> selected.</>
          ) : (
            <>
              Bespoke measurements saved
              {selection.fullLining ? ", with full lining" : ""}.{" "}
              <span className="text-ink-600">
                Stitching adds {product.stitching_days} days.
              </span>
            </>
          )}
        </div>
      )}

      {product.supports_bespoke && (
        <p className="mt-4 text-xs leading-relaxed text-ink-600">
          Bespoke tailoring from {formatINR(product.base_price)} plus
          surcharge · {product.stitching_days} days
        </p>
      )}

      <FitDrawer
        open={open}
        onClose={() => setOpen(false)}
        garment={product.garment_type as GarmentType}
        productName={product.name}
        supportsBespoke={product.supports_bespoke}
        onSubmit={setSelection}
      />
    </div>
  );
}
