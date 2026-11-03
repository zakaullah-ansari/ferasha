import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { CartDrawer } from "@/components/CartDrawer";
import { useCartStore } from "@/store/useCartStore";

import { BAG } from "../tests/fixtures/commerce";

/** The bag (shadcn Sheet). State lives in the real zustand store. */
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
