import { AtelierStory } from "@/components/home/AtelierStory";
import { Hero } from "@/components/home/Hero";
import { ModestyPromise } from "@/components/home/ModestyPromise";
import { OccasionTiles } from "@/components/home/OccasionTiles";
import { TabbedProductRail } from "@/components/product/TabbedProductRail";
import { TrustStrip } from "@/components/site/TrustStrip";
import { api } from "@/lib/api/client";
import { CATEGORY_NAV } from "@/lib/navigation";

/** ISR: the catalogue is SEO-critical and changes rarely. */
export const revalidate = 60;

export default async function HomePage() {
  // All tabs load together on the server (newest first, the API's default
  // order). "All" fails the page as before; a category that fails to load
  // just loses its tab, rather than taking the homepage down with it.
  const [all, ...byCategory] = await Promise.allSettled([
    api.listProducts({ page_size: 8 }),
    ...CATEGORY_NAV.map((link) => api.listProducts({ page_size: 8, category: link.category })),
  ]);
  if (all.status === "rejected") throw all.reason;

  const tabs = [
    { label: "All", href: "/products", products: all.value.results, viewAllLabel: "All garments" },
    ...CATEGORY_NAV.flatMap((link, index) => {
      const result = byCategory[index];
      return result?.status === "fulfilled" ? [{ label: link.label, href: link.href, products: result.value.results }] : [];
    }),
  ];

  return (
    <>
      <Hero />
      {/* What the shop promises, straight after the first impression. The list is labelled; the frame is not, so it is announced once. */}
      <div className="border-y border-border/60">
        <TrustStrip className="mx-auto max-w-6xl px-5 py-8" />
      </div>
      <OccasionTiles />
      <TabbedProductRail eyebrow="The edit" title="New this season" tabs={tabs} />
      <ModestyPromise />
      <AtelierStory />
    </>
  );
}
