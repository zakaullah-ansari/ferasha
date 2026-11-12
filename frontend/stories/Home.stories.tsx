import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { AtelierStory } from "@/components/home/AtelierStory";
import { Hero } from "@/components/home/Hero";
import { ModestyPromise } from "@/components/home/ModestyPromise";
import { OccasionTiles } from "@/components/home/OccasionTiles";
import { ProductRail } from "@/components/product/ProductRail";
import { TabbedProductRail } from "@/components/product/TabbedProductRail";
import { MobileNav } from "@/components/site/MobileNav";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import type { ProductSummary } from "@/lib/api/types";

import { PRODUCT } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** The homepage, section by section ("The Atelier Edit" direction). */
const meta = {
  title: "Home",
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const EDIT: ProductSummary[] = [
  "Karachi Lawn Chikankari - Ivory",
  "Velvet Gharara - Emerald",
  "Raw Silk Blouse - Gold",
  "Banarasi Bridal Lehenga - Crimson",
].map((name, index) => ({ ...PRODUCT, id: `edit-${index}`, slug: `edit-${index}`, name }));

const guest = () => mockFetch([{ path: "/api/session/me", body: { user: null } }]);

export const Header: Story = { beforeEach: guest, render: () => <SiteHeader /> };
export const HeroSection: Story = { render: () => <Hero /> };
export const Occasions: Story = { render: () => <OccasionTiles /> };
export const Edit: Story = {
  render: () => <ProductRail eyebrow="The edit" title="New this season" products={EDIT} href="/products" />,
};
/**
 * The homepage edit, one tab per category. Empty categories (here Sharara &
 * Gharara) drop out rather than showing a dead end; "View all" follows the tab.
 */
export const EditTabs: Story = {
  render: () => (
    <TabbedProductRail
      eyebrow="The edit"
      title="New this season"
      tabs={[
        { label: "All", href: "/products", products: EDIT, viewAllLabel: "All garments" },
        { label: "Suits", href: "/products?category=suits", products: EDIT.slice(0, 2) },
        { label: "Bridal", href: "/products?category=bridal", products: EDIT.slice(3) },
        { label: "Sharara & Gharara", href: "/products?category=sharara-gharara", products: [] },
      ]}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.queryByRole("tab", { name: "Sharara & Gharara" })).not.toBeInTheDocument();
    await expect(canvas.getByRole("link", { name: /All garments/ })).toHaveAttribute("href", "/products");
    await userEvent.click(canvas.getByRole("tab", { name: "Bridal" }));
    await expect(canvas.getByRole("tab", { name: "Bridal" })).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("link", { name: /View all bridal/ })).toHaveAttribute("href", "/products?category=bridal");
    await expect(await canvas.findByText("Banarasi Bridal Lehenga - Crimson")).toBeInTheDocument();
  },
};
export const PromiseSection: Story = { render: () => <ModestyPromise /> };
export const Atelier: Story = { render: () => <AtelierStory /> };
export const Footer: Story = { render: () => <SiteFooter /> };

/** Phone menu: categories, occasions, the atelier. */
export const PhoneMenu: Story = {
  globals: { viewport: { value: "mobile1" } },
  render: () => (
    <div className="p-4">
      <MobileNav />
    </div>
  ),
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Open menu" }));
    const menu = within(canvasElement.ownerDocument.body);
    await expect(await menu.findByRole("navigation", { name: "Menu" })).toBeInTheDocument();
    await expect(menu.getByRole("link", { name: "Shop fully covered" })).toBeInTheDocument();
  },
};
