import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, screen } from "storybook/test";

import { CartDrawer } from "@/components/CartDrawer";
import { useCartStore } from "@/store/useCartStore";

import { BAG, BESPOKE_LINE } from "../tests/fixtures/commerce";

/** The bag: the theme's rounded drawer, from the bottom on phones and from the right from tablet up. State lives in the real zustand store. */
const meta = {
  title: "Commerce/CartDrawer",
  component: CartDrawer,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof CartDrawer>;

export default meta;
type Story = StoryObj<typeof meta>;

function openWith(items: typeof BAG) {
  return () => {
    useCartStore.setState({ items, isOpen: true });
    return () => useCartStore.setState({ items: [], isOpen: false });
  };
}

export const WithItems: Story = { beforeEach: openWith(BAG) };
export const Empty: Story = { beforeEach: openWith([]) };

/** A ready-made piece beside a made-to-measure one: the bespoke line is one piece, with no quantity stepper. */
export const WithABespokePiece: Story = {
  beforeEach: openWith([BAG[0]!, BESPOKE_LINE]),
  play: async () => {
    await expect(await screen.findByText("Made to measure · stitched for you")).toBeInTheDocument();
    // Only the ready-made line can change quantity.
    await expect(screen.getAllByRole("button", { name: /Increase quantity/ })).toHaveLength(1);
  },
};
