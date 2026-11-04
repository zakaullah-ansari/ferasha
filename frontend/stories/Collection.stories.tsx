import { getRouter } from "@storybook/nextjs-vite/navigation.mock";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { CatalogPagination } from "@/components/catalog/CatalogControls";
import { CatalogNavigation } from "@/components/catalog/CatalogNavigation";
import { CollectionView } from "@/components/catalog/CollectionView";
import { FilterPanel } from "@/components/catalog/FilterPanel";
import type { ProductSummary } from "@/lib/api/types";
import { parseCatalogQuery } from "@/lib/catalog-query";

import { FACETS, PRODUCT } from "../tests/fixtures/commerce";

/** The collection page (/products): filters, chips, sort and pages, all held in the URL. */
const meta = {
  title: "Collection",
  parameters: { layout: "fullscreen", nextjs: { navigation: { pathname: "/products" } } },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const GARMENTS: ProductSummary[] = [
  ["Karachi Lawn Chikankari - Ivory", "4200.00"],
  ["Velvet Gharara - Emerald", "64500.00"],
  ["Raw Silk Blouse - Gold", "6800.00"],
  ["Banarasi Bridal Lehenga - Crimson", "189000.00"],
  ["Chiffon Nikah Suit - Blush", "42000.00"],
  ["Cotton Everyday Suit - Sage", "1890.00"],
].map(([name, price], index) => ({
  ...PRODUCT,
  id: `garment-${index}`,
  slug: `garment-${index}`,
  name: name!,
  base_price: price!,
  supports_bespoke: index % 2 === 0,
}));

const BRIDAL = { id: "c-bridal", name: "Bridal", slug: "bridal", description: "Lehengas, gharara and sharara for the day itself, lined and fully covered." };

export const Page: Story = {
  render: () => (
    <CollectionView query={parseCatalogQuery({})} facets={FACETS} products={GARMENTS} count={GARMENTS.length} />
  ),
};

/** Arriving from the Bridal menu with two filters set: the chips say what is narrowing the page. */
export const Filtered: Story = {
  render: () => (
    <CollectionView
      query={parseCatalogQuery({ category: "bridal", fully_covered: "true", occasion: ["nikah", "walima"], price_min: "25000", price_max: "100000" })}
      facets={{ ...FACETS, total: 2 }}
      products={GARMENTS.slice(1, 3)}
      count={2}
      category={BRIDAL}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Remove filter: Nikah" }));
    await expect(getRouter().push).toHaveBeenLastCalledWith(
      "/products?category=bridal&occasion=walima&fully_covered=true&price_min=25000&price_max=100000",
      { scroll: false },
    );
    await userEvent.click(canvas.getByRole("button", { name: "Clear all" }));
    await expect(getRouter().push).toHaveBeenLastCalledWith("/products?category=bridal", { scroll: false });
  },
};

export const Empty: Story = {
  render: () => (
    <CollectionView
      query={parseCatalogQuery({ fabric: "velvet", no_slit: "true" })}
      facets={{ ...FACETS, total: 0 }}
      products={[]}
      count={0}
    />
  ),
};

/** Modesty first, with live counts; a choice that would empty the page cannot be ticked. */
export const Filters: Story = {
  parameters: { layout: "padded" },
  render: () => (
    <CatalogNavigation query={parseCatalogQuery({ occasion: "eid" })}>
      <div className="max-w-60">
        <FilterPanel facets={FACETS} />
      </div>
    </CatalogNavigation>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("checkbox", { name: "No slit" })).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(canvas.getByRole("checkbox", { name: "Fully covered" }));
    await expect(getRouter().push).toHaveBeenLastCalledWith("/products?occasion=eid&fully_covered=true", { scroll: false });
  },
};

export const Pages: Story = {
  parameters: { layout: "padded" },
  render: () => (
    <CatalogNavigation query={parseCatalogQuery({ occasion: "bridal", page: "5" })}>
      <CatalogPagination pageCount={12} />
    </CatalogNavigation>
  ),
  play: async ({ canvasElement }) => {
    const next = within(canvasElement).getByRole("link", { name: "Go to next page" });
    await expect(next).toHaveAttribute("href", "/products?occasion=bridal&page=6");
    await userEvent.click(next);
    await expect(getRouter().push).toHaveBeenLastCalledWith("/products?occasion=bridal&page=6", { scroll: true });
  },
};
