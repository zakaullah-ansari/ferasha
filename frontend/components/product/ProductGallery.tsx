"use client";

import { useState } from "react";

import { Lens } from "@/components/ui/lens";
import type { ProductImage } from "@/lib/api/types";
import { cn } from "@/lib/cn";

interface ProductGalleryProps {
  readonly images: readonly ProductImage[];
  readonly name: string;
}

/**
 * Main image with the fabric lens, plus thumbnails (left on desktop, below on
 * phones). Only images the privacy pipeline approved have a URL; anything else
 * is never shown. On phones the lens does nothing - customers pinch-zoom.
 */
export function ProductGallery({ images, name }: ProductGalleryProps) {
  const shown = images
    .filter((image): image is ProductImage & { url: string } => Boolean(image.url))
    .sort((a, b) => Number(b.is_primary) - Number(a.is_primary) || a.display_order - b.display_order);
  const [index, setIndex] = useState(0);
  const current = shown[Math.min(index, shown.length - 1)];

  if (!current) {
    return (
      <div className="flex aspect-[4/5] flex-col items-center justify-center gap-2 rounded-[2rem] bg-muted text-center">
        <span className="font-display text-2xl text-muted-foreground">Photography coming soon</span>
        <span className="max-w-60 text-xs text-muted-foreground">
          Every photo is checked by our privacy pipeline before it appears here.
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col-reverse gap-4 md:flex-row">
      {shown.length > 1 && (
        <ul className="flex gap-3 overflow-x-auto md:flex-col" aria-label="Product images">
          {shown.map((image, position) => (
            <li key={image.id} className="shrink-0">
              <button
                type="button"
                onClick={() => setIndex(position)}
                aria-label={`Show image ${position + 1} of ${shown.length}`}
                aria-current={position === index ? "true" : undefined}
                className={cn(
                  "block w-16 overflow-hidden rounded-xl border-2 transition-opacity duration-300",
                  position === index ? "border-primary" : "border-transparent opacity-70 hover:opacity-100",
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={image.url} alt="" className="aspect-[4/5] w-full object-cover" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex-1">
        <Lens zoomFactor={2.2} lensSize={200} ariaLabel={`Zoom into ${name}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={current.url}
            alt={current.alt_text || name}
            className="aspect-[4/5] w-full rounded-[2rem] object-cover"
          />
        </Lens>
        <p className="mt-2 hidden text-center text-xs text-muted-foreground md:block">
          Hover over the photo to see the fabric up close
        </p>
      </div>
    </div>
  );
}
