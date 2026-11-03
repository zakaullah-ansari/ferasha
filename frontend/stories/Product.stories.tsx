import type { Meta, StoryObj } from "@storybook/nextjs-vite";

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
