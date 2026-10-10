import { CoverageScore, ModestyBadgeList } from "@/components/ModestyBadge";
import type { ProductSummary } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

/**
 * Listing card.
 *
 * The card shows advisories, not just flattering badges. It is tempting to
 * keep caveats off the grid for a cleaner look; that converts better and
 * returns worse, and it is dishonest. Advisories render first.
 */
export function ProductCard({ product }: { product: ProductSummary }) {
  const hasAdvisories = product.modesty.advisories.length > 0;

  return (
    <article className="group flex flex-col">
      <a
        href={`/products/${product.slug}`}
        className="flex flex-1 flex-col focus-visible:outline-none"
      >
        {/* Light grey ground so embellished garments and cutouts pop — the
            Nike/COS treatment, and the correct choice for zardozi and gota
            which are always shot on light. */}
        <div className="relative aspect-[4/5] overflow-hidden rounded-lg bg-ink-100">
          {product.primary_image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.primary_image}
              alt=""
              loading="lazy"
              className="size-full object-cover transition-transform duration-500 ease-[cubic-bezier(.22,1,.36,1)] group-hover:scale-[1.03]"
            />
          ) : (
            <div className="flex size-full items-center justify-center">
              <span className="font-display text-sm text-ink-500">
                Imagery in preparation
              </span>
            </div>
          )}
          {product.supports_bespoke && (
            <span className="absolute left-3 top-3 rounded-full bg-ivory/95 px-2.5 py-1 text-[0.65rem] font-medium tracking-wide text-ink-800 uppercase">
              Bespoke
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-1 flex-col">
          <h3 className="font-display text-lg leading-snug text-ink-900 group-hover:underline">
            {product.name}
          </h3>
          <p className="mt-0.5 text-xs tracking-wide text-ink-600 capitalize">
            {product.fabric.replace(/_/g, " ")} ·{" "}
            {product.work_type.replace(/_/g, " ")}
          </p>

          <p className="mt-2 text-base text-ink-900">
            {formatINR(product.base_price)}
          </p>

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
