import { CoverageScore, ModestyBadgeList } from "@/components/ModestyBadge";
import { Price } from "@/components/product/Price";
import { Badge } from "@/components/ui/badge";
import type { ProductSummary } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { GLASS } from "@/lib/glass";
import { isNewArrival, percentOff } from "@/lib/merchandising";

/**
 * Listing card.
 *
 * The card shows advisories, not just flattering badges. It is tempting to
 * keep caveats off the grid for a cleaner look; that converts better and
 * returns worse, and it is dishonest. Advisories render first.
 *
 * Merchandising labels (New, % off, Bespoke) sit on the photo, as on the
 * reference stores, so they never push the coverage line down the card.
 */
export function ProductCard({ product }: { product: ProductSummary }) {
  const hasAdvisories = product.modesty.advisories.length > 0;
  const saving = percentOff(product.base_price, product.compare_at_price);
  const isNew = isNewArrival(product.created_at);

  return (
    <article className="group flex flex-col">
      <a
        href={`/products/${product.slug}`}
        className="flex flex-1 flex-col focus-visible:outline-none"
      >
        {/* Light grey ground so embellished garments and cutouts pop — the
            Nike/COS treatment, and the correct choice for zardozi and gota
            which are always shot on light. */}
        <div className="relative aspect-[4/5] overflow-hidden rounded-lg bg-muted transition-shadow duration-500 ease-luxury group-hover:shadow-xl group-hover:shadow-primary/10">
          {product.primary_image ? (
            <>
              {/* The link's text names the piece, so the photos are decorative here. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={product.primary_image.url}
                alt=""
                loading="lazy"
                className="size-full object-cover transition-transform duration-500 ease-luxury group-hover:scale-[1.03]"
              />
              {product.secondary_image && (
                // A second angle on hover or keyboard focus; no fade under reduced motion.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={product.secondary_image.url}
                  alt=""
                  loading="lazy"
                  className="absolute inset-0 size-full object-cover opacity-0 transition-opacity duration-300 ease-luxury group-focus-within:opacity-100 group-hover:opacity-100 motion-reduce:transition-none"
                />
              )}
            </>
          ) : (
            <div className="flex size-full items-center justify-center">
              <span className="font-display text-sm text-muted-foreground">
                Imagery in preparation
              </span>
            </div>
          )}
          {(isNew || product.supports_bespoke) && (
            <span className="absolute top-3 left-3 flex flex-col items-start gap-1.5">
              {isNew && (
                // Fixed gold-on-ink pair (contrast-tested), so it reads the same in dark mode.
                <Badge className="bg-gold-200 tracking-wide text-ink-900 uppercase">New</Badge>
              )}
              {product.supports_bespoke && (
                <span className={cn("rounded-full px-2.5 py-1 text-[0.65rem] font-medium tracking-wide text-foreground uppercase", GLASS.float)}>
                  Bespoke
                </span>
              )}
            </span>
          )}
          {saving !== null && (
            <Badge className="absolute top-3 right-3">{saving}% off</Badge>
          )}
        </div>

        <div className="mt-3 flex flex-1 flex-col">
          <h3 className="font-display text-lg leading-snug text-foreground group-hover:underline">
            {product.name}
          </h3>
          <p className="mt-0.5 text-xs tracking-wide text-muted-foreground capitalize">
            {product.fabric.replace(/_/g, " ")} ·{" "}
            {product.work_type.replace(/_/g, " ")}
          </p>

          <Price price={product.base_price} compareAt={product.compare_at_price} className="mt-2 text-base text-foreground" />


          <div className="mt-3 space-y-2">
            {/* Badges are capped for layout; advisories never are. */}
            <ModestyBadgeList modesty={product.modesty} limit={hasAdvisories ? 1 : 3} />
            <CoverageScore score={product.modesty.coverage_score} />
          </div>
        </div>
      </a>
    </article>
  );
}
