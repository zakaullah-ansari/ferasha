"use client";

import Link from "next/link";

import { ProductCard } from "@/components/ProductCard";
import { BlurFade } from "@/components/ui/blur-fade";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import type { ProductSummary } from "@/lib/api/types";

/**
 * The featured edit: a swipeable row. Manual only - no autoplay, which would
 * need a pause control (WCAG 2.2.2) and which shoppers mostly dislike.
 */
export function FeaturedEdit({ products }: { products: readonly ProductSummary[] }) {
  if (products.length === 0) return null;

  return (
    <section aria-labelledby="edit-heading" className="mx-auto max-w-6xl px-5 py-16">
      <BlurFade inView className="flex items-end justify-between gap-6">
        <div>
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">The edit</p>
          <h2 id="edit-heading" className="mt-3 font-display text-display-sm">
            New this season
          </h2>
        </div>
        <Link href="/products" className="shrink-0 text-sm text-primary underline-offset-4 hover:underline">
          All garments
        </Link>
      </BlurFade>
      <Carousel opts={{ align: "start" }} className="mt-10" aria-label="New this season">
        <CarouselContent>
          {products.map((product) => (
            <CarouselItem key={product.id} className="basis-3/4 sm:basis-1/2 lg:basis-1/3">
              <ProductCard product={product} />
            </CarouselItem>
          ))}
        </CarouselContent>
        <div className="mt-6 flex justify-end gap-2">
          <CarouselPrevious className="static translate-y-0" />
          <CarouselNext className="static translate-y-0" />
        </div>
      </Carousel>
    </section>
  );
}
