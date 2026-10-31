import { notFound } from "next/navigation";

import { CoverageScore, ModestyBadgeList } from "@/components/ModestyBadge";
import { ProductPurchasePanel } from "@/components/ProductPurchasePanel";
import { ApiError, api } from "@/lib/api/client";
import { formatINR } from "@/lib/format";

export const revalidate = 60;

async function load(slug: string) {
  try {
    return await api.getProduct(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  try {
    const product = await api.getProduct(slug);
    return {
      title: product.name,
      description: product.description.slice(0, 160),
    };
  } catch {
    return { title: "Garment" };
  }
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = await load(slug);

  const attributes = [
    ["Fabric", product.fabric],
    ["Work", product.work_type],
    ["Occasion", product.occasion],
    ["Garment", product.garment_type],
  ] as const;

  return (
    <article className="mx-auto max-w-6xl px-5 py-10">
      <div className="grid gap-10 md:grid-cols-2 md:gap-14">
        {/* Gallery */}
        <div className="aspect-[4/5] overflow-hidden rounded-xl bg-muted">
          {product.primary_image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.primary_image}
              alt={product.name}
              className="size-full object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center">
              <span className="font-display text-muted-foreground">
                Imagery in preparation
              </span>
            </div>
          )}
        </div>

        {/* Detail */}
        <div>
          <h1 className="font-display text-[length:var(--text-display-sm)] leading-tight text-foreground">
            {product.name}
          </h1>

          <p className="mt-3 text-xl text-foreground">
            {formatINR(product.base_price)}
            {product.compare_at_price && (
              <span className="ml-3 text-sm text-muted-foreground line-through">
                {formatINR(product.compare_at_price)}
              </span>
            )}
          </p>

          {/*
            Modesty disclosure sits above the fold and above the buy button,
            not buried in a tab. If a garment is sheer, the customer learns
            that before deciding, not after unwrapping it.
          */}
          <div className="mt-6 rounded-xl border border-border bg-card p-4">
            <CoverageScore score={product.modesty.coverage_score} />
            <ModestyBadgeList modesty={product.modesty} className="mt-3" />
            {product.modesty.advisories.length > 0 && (
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                Please read the advisories above before ordering.
              </p>
            )}
          </div>

          <div className="mt-6">
            <ProductPurchasePanel product={product} />
          </div>

          {product.description && (
            <p className="mt-8 text-sm leading-relaxed text-muted-foreground">
              {product.description}
            </p>
          )}

          <dl className="mt-8 grid grid-cols-2 gap-y-3 border-t border-border pt-6 text-sm">
            {attributes.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs tracking-wide text-muted-foreground uppercase">
                  {label}
                </dt>
                <dd className="mt-0.5 text-foreground capitalize">
                  {value.replace(/_/g, " ")}
                </dd>
              </div>
            ))}
          </dl>

          {product.care_instructions && (
            <div className="mt-6 border-t border-border pt-6">
              <h2 className="text-xs tracking-wide text-muted-foreground uppercase">
                Care
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {product.care_instructions}
              </p>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
