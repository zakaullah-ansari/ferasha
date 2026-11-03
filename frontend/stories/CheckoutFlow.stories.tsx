import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { CheckoutFlow } from "@/components/CheckoutFlow";
import { useCartStore } from "@/store/useCartStore";

import { BAG } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** Checkout entry: the browser bag replaces the server cart, then the stepper. */
const meta = {
  title: "Checkout/CheckoutFlow",
  component: CheckoutFlow,
  parameters: { layout: "padded" },
} satisfies Meta<typeof CheckoutFlow>;

export default meta;
type Story = StoryObj<typeof meta>;

function withBag(items = BAG) {
  useCartStore.setState({ items, isOpen: false });
  return () => useCartStore.setState({ items: [], isOpen: false });
}

const MERGE_URL = "/api/v1/cart/merge/";

export const Ready: Story = {
  beforeEach: () => {
    const restoreBag = withBag();
    const restoreFetch = mockFetch([{ method: "POST", path: MERGE_URL, body: { skipped: [] } }]);
    return () => {
      restoreFetch();
      restoreBag();
    };
  },
};

/** A piece sold out while it sat in the bag. */
export const ItemNoLongerAvailable: Story = {
  beforeEach: () => {
    const restoreBag = withBag();
    const restoreFetch = mockFetch([{ method: "POST", path: MERGE_URL, body: { skipped: ["v-m-sage"] } }]);
    return () => {
      restoreFetch();
      restoreBag();
    };
  },
};

export const Preparing: Story = {
  beforeEach: () => {
    const restoreBag = withBag();
    const restoreFetch = mockFetch([{ method: "POST", path: MERGE_URL, body: { skipped: [] }, delayMs: 60_000 }]);
    return () => {
      restoreFetch();
      restoreBag();
    };
  },
};

export const EmptyBag: Story = { beforeEach: () => withBag([]) };
