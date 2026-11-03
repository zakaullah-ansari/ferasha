import { AtelierStory } from "@/components/home/AtelierStory";
import { FeaturedEdit } from "@/components/home/FeaturedEdit";
import { Hero } from "@/components/home/Hero";
import { ModestyPromise } from "@/components/home/ModestyPromise";
import { OccasionTiles } from "@/components/home/OccasionTiles";
import { api } from "@/lib/api/client";

/** ISR: the catalogue is SEO-critical and changes rarely. */
export const revalidate = 60;

export default async function HomePage() {
  const { results } = await api.listProducts({ page_size: 8 });

  return (
    <>
      <Hero />
      <OccasionTiles />
      <FeaturedEdit products={results} />
      <ModestyPromise />
      <AtelierStory />
    </>
  );
}
