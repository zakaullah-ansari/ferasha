"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

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

interface ProductRailProps {
  readonly eyebrow: string;
  readonly title: string;
  readonly products: readonly ProductSummary[];
  readonly href: string;
  readonly hrefLabel?: string;
}

/**
 * A titled, swipeable row of products (homepage edit, "Complete the look").
 * Manual only - no autoplay, which would need a pause control (WCAG 2.2.2)
 * and which shoppers mostly dislike.
 */
export function ProductRail({ eyebrow, title, products, href, hrefLabel = "View all" }: ProductRailProps) {
  if (products.length === 0) return null;
  const headingId = railHeadingId(eyebrow);

  return (
    <section aria-labelledby={headingId} className="mx-auto max-w-6xl px-5 py-16">
      <RailHeading eyebrow={eyebrow} title={title} headingId={headingId}>
        <ViewAllLink href={href} label={hrefLabel} />
      </RailHeading>
      <ProductCarousel products={products} label={title} className="mt-10" />
    </section>
  );
}

export const railHeadingId = (eyebrow: string) => `rail-${eyebrow.toLowerCase().replace(/\W+/g, "-")}`;

/** Eyebrow and heading on the left, an action (usually "View all") on the right. */
export function RailHeading({
  eyebrow,
  title,
  headingId,
  children,
}: {
  readonly eyebrow: string;
  readonly title: string;
  readonly headingId: string;
  readonly children?: ReactNode;
}) {
  return (
    <BlurFade inView className="flex items-end justify-between gap-6">
      <div>
        <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">{eyebrow}</p>
        <h2 id={headingId} className="mt-3 font-display text-display-sm">
          {title}
        </h2>
      </div>
      {children}
    </BlurFade>
  );
}

export function ViewAllLink({ href, label = "View all" }: { readonly href: string; readonly label?: string }) {
  return (
    <Link href={href} className="group/link inline-flex shrink-0 items-center gap-1 text-sm text-primary underline-offset-4 hover:underline">
      {label}
      <ArrowRight aria-hidden="true" className="size-4 transition-transform duration-300 group-hover/link:translate-x-1" />
    </Link>
  );
}

/** The swipeable row itself, shared by the plain rail and the tabbed one. */
export function ProductCarousel({
  products,
  label,
  className,
}: {
  readonly products: readonly ProductSummary[];
  readonly label: string;
  readonly className?: string;
}) {
  return (
    <Carousel opts={{ align: "start" }} className={className} aria-label={label}>
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
  );
}
