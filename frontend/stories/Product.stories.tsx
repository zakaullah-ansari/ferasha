import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, within } from "storybook/test";

import { ProductCard } from "@/components/ProductCard";
import { ProductPurchasePanel } from "@/components/ProductPurchasePanel";

import { PRODUCT } from "../tests/fixtures/commerce";

/** Product surfaces: the listing card and the purchase panel on the PDP. */
const meta = {
  title: "Commerce/Product",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const WITH_ADVISORY = {
  ...PRODUCT,
  name: "Organza Overlay Suit - Blush",
  modesty: {
    coverage_score: 48,
    badges: [{ code: "modest_neckline", label: "Modest neckline" }],
    advisories: [
      { code: "sheer_overlay", label: "Sheer overlay" },
      { code: "slip_required", label: "Slip required" },
    ],
  },
};

export const Card: Story = {
  render: () => (
    <div className="grid max-w-3xl grid-cols-2 gap-6">
      <ProductCard product={PRODUCT} />
      <ProductCard product={WITH_ADVISORY} />
    </div>
  ),
};

const ON_SALE = {
  ...PRODUCT,
  id: "on-sale",
  name: "Velvet Gharara - Emerald",
  base_price: "13592.00",
  compare_at_price: "16990.00",
  supports_bespoke: false,
};

/** Listed today, so it carries "New"; also bespoke, so the labels stack. */
const NEW_ARRIVAL = { ...PRODUCT, id: "new", name: "Raw Silk Kurta - Gold", created_at: new Date().toISOString() };

/**
 * Merchandising labels on the photo: "New" and "Bespoke" stack top left, the
 * saving sits top right, and the struck-through price follows the sale price.
 * Exactly 20% off reads 20%, never 19% (a floating-point trap).
 */
export const CardLabels: Story = {
  render: () => (
    <div className="grid max-w-3xl grid-cols-2 gap-6">
      <ProductCard product={ON_SALE} />
      <ProductCard product={NEW_ARRIVAL} />
    </div>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("20% off")).toBeInTheDocument();
    await expect(canvas.getByText("New")).toBeInTheDocument();
    // The old price is a <del>, announced as "was ..." to screen readers.
    const was = canvasElement.querySelector("del");
    await expect(was?.textContent).toMatch(/was\s*₹\s?16,990/);
  },
};

/** Two colours, sizes per colour; L Ivory is out of stock and not offered. */
export const PurchasePanel: Story = {
  render: () => (
    <div className="max-w-md">
      <ProductPurchasePanel product={PRODUCT} />
    </div>
  ),
};

export const PurchasePanelSoldOut: Story = {
  render: () => (
    <div className="max-w-md">
      <ProductPurchasePanel
        product={{ ...PRODUCT, variants: PRODUCT.variants.map((v) => ({ ...v, in_stock: false })) }}
      />
    </div>
  ),
};
