import { ProductCard } from "@/components/ProductCard";
import { api } from "@/lib/api/client";

export const revalidate = 60;

export const metadata = { title: "Collection" };

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const flat: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") flat[key] = value;
  }

  const { results, count } = await api.listProducts(flat);

  return (
    <section className="mx-auto max-w-6xl px-5 py-14">
      <h1 className="font-display text-3xl text-foreground">Collection</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {count} {count === 1 ? "garment" : "garments"}
      </p>

      {results.length === 0 ? (
        <p className="mt-12 text-muted-foreground">
          No garments match these filters yet.
        </p>
      ) : (
        <div className="mt-10 grid grid-cols-2 gap-x-5 gap-y-10 md:grid-cols-3">
          {results.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}
