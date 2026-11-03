import { Truck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CoverageScore, ModestyBadgeList } from "@/components/ModestyBadge";
import { ProductDetails } from "@/components/product/ProductDetails";
import { ProductGallery } from "@/components/product/ProductGallery";
import { ProductRail } from "@/components/product/ProductRail";
import { ProductPurchasePanel } from "@/components/ProductPurchasePanel";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { ApiError, api } from "@/lib/api/client";
import { DELIVERY } from "@/lib/delivery";
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
  const related = await api
    .listProducts({ category: product.category.slug, page_size: 9 })
    .then(({ results }) => results.filter((item) => item.id !== product.id).slice(0, 8))
    .catch(() => []);

  return (
    // Bottom padding on phones keeps content clear of the pinned buy bar.
    <article className="max-md:pb-24">
      <div className="mx-auto max-w-6xl px-5 pt-6">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink render={<Link href="/" />}>Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink render={<Link href={`/products?category=${product.category.slug}`} />}>
                {product.category.name}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage className="line-clamp-1">{product.name}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-8 md:grid-cols-[1.15fr_0.85fr] md:gap-14">
        <ProductGallery images={product.images} name={product.name} />

        <div className="md:sticky md:top-24 md:self-start">
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">{product.category.name}</p>
          <h1 className="mt-3 font-display text-display-sm leading-tight">{product.name}</h1>

          <p className="mt-3 text-xl">
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
          <div className="mt-6 rounded-2xl border bg-card p-4">
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

          <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
            <Truck aria-hidden="true" className="size-4" />
            {DELIVERY.summary}
          </p>

          <div className="mt-8">
            <ProductDetails product={product} />
          </div>
        </div>
      </div>

      <ProductRail
        eyebrow="Complete the look"
        title={`More from ${product.category.name}`}
        products={related}
        href={`/products?category=${product.category.slug}`}
      />
    </article>
  );
}
