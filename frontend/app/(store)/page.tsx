import { AtelierStory } from "@/components/home/AtelierStory";
import { Hero } from "@/components/home/Hero";
import { ModestyPromise } from "@/components/home/ModestyPromise";
import { OccasionTiles } from "@/components/home/OccasionTiles";
import { ProductRail } from "@/components/product/ProductRail";
import { TrustStrip } from "@/components/site/TrustStrip";
import { api } from "@/lib/api/client";

/** ISR: the catalogue is SEO-critical and changes rarely. */
export const revalidate = 60;

export default async function HomePage() {
  const { results } = await api.listProducts({ page_size: 8 });

  return (
    <>
      <Hero />
      {/* What the shop promises, straight after the first impression. The list is labelled; the frame is not, so it is announced once. */}
      <div className="border-y border-border/60">
        <TrustStrip className="mx-auto max-w-6xl px-5 py-8" />
      </div>
      <OccasionTiles />
      <ProductRail
        eyebrow="The edit"
        title="New this season"
        products={results}
        href="/products"
        hrefLabel="All garments"
      />
      <ModestyPromise />
      <AtelierStory />
    </>
  );
}
