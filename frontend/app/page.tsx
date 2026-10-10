import { ProductCard } from "@/components/ProductCard";
import { api } from "@/lib/api/client";

/** ISR: the catalogue is SEO-critical and changes rarely. */
export const revalidate = 60;

export default async function HomePage() {
  const { results } = await api.listProducts({ page_size: 6 });

  return (
    <>
      <section className="mx-auto max-w-6xl px-5 pb-16 pt-20">
        <p className="text-xs tracking-[0.2em] text-ink-600 uppercase">
          Mumbai · Est. 2026
        </p>
        <h1 className="mt-4 max-w-3xl text-[length:var(--text-display-lg)] leading-[1.05] text-ink-900">
          Modest luxury, cut to order.
        </h1>
        <p className="mt-6 max-w-xl text-base leading-relaxed text-ink-700">
          Pakistani and Punjabi suits, bridal lehengas, sharara and gharara.
          Every garment publishes its coverage honestly — so you know exactly
          what arrives.
        </p>
        <a
          href="/products"
          className="mt-8 inline-flex min-h-12 items-center rounded-full bg-ink-900 px-7 text-sm tracking-wide text-ivory hover:bg-ink-800"
        >
          View the collection
        </a>
      </section>

      <section className="mx-auto max-w-6xl px-5">
        <div className="flex items-baseline justify-between border-t border-ink-200 pt-10">
          <h2 className="font-display text-2xl text-ink-900">Latest pieces</h2>
          <a href="/products" className="text-sm text-gold-700 hover:text-gold-800">
            All {results.length > 0 ? "garments" : "pieces"} →
          </a>
        </div>
        <div className="mt-8 grid grid-cols-2 gap-x-5 gap-y-10 md:grid-cols-3">
          {results.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>
    </>
  );
}
