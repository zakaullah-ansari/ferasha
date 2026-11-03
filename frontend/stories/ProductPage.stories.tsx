import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { CoverageMap } from "@/components/product/CoverageMap";
import { ProductDetails } from "@/components/product/ProductDetails";
import { ProductGallery } from "@/components/product/ProductGallery";
import type { ProductDetail } from "@/lib/api/types";

import { PRODUCT } from "../tests/fixtures/commerce";
import suit from "./assets/kausar-lawn-suit.jpg";

/** Product page building blocks. */
const meta = {
  title: "Product page",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const IMAGES = [0, 1, 2].map((n) => ({
  id: `img-${n}`,
  url: suit.src,
  alt_text: "Mint lawn suit with a printed dupatta",
  display_order: n,
  is_primary: n === 0,
}));

/** Organza overlay: honest about a less covering garment. */
const REVEALING: ProductDetail = {
  ...PRODUCT,
  name: "Organza Overlay Suit - Blush",
  neckline_modesty: "moderate",
  sleeve_coverage: "elbow",
  back_coverage: "deep",
  slit_coverage: "knee",
  is_opaque: false,
  has_full_lining: false,
  requires_slip: true,
  is_sheer_overlay_only: true,
};

export const GalleryWithPhotos: Story = {
  render: () => (
    <div className="max-w-xl">
      <ProductGallery images={IMAGES} name={PRODUCT.name} />
    </div>
  ),
};

/** Before the shoot: no unapproved image is ever shown. */
export const GalleryAwaitingPhotos: Story = {
  render: () => (
    <div className="max-w-md">
      <ProductGallery images={[{ ...IMAGES[0]!, url: null }]} name={PRODUCT.name} />
    </div>
  ),
};

export const CoverageFullyCovered: Story = {
  render: () => (
    <div className="max-w-md">
      <CoverageMap product={PRODUCT} />
    </div>
  ),
};

export const CoverageRevealing: Story = {
  render: () => (
    <div className="max-w-md">
      <CoverageMap product={REVEALING} />
    </div>
  ),
};

export const Details: Story = {
  render: () => (
    <div className="max-w-md">
      <ProductDetails product={PRODUCT} />
    </div>
  ),
};
