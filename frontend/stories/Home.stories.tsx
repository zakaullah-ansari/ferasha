import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { AtelierStory } from "@/components/home/AtelierStory";
import { Hero } from "@/components/home/Hero";
import { ModestyPromise } from "@/components/home/ModestyPromise";
import { OccasionTiles } from "@/components/home/OccasionTiles";
import { ProductRail } from "@/components/product/ProductRail";
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
