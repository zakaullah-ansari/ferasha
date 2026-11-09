import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, within } from "storybook/test";

import { OrderPlacedTick, WhatHappensNext } from "@/components/account/OrderPlaced";
import { TrustStrip } from "@/components/site/TrustStrip";

/** The shop's promises, and the moment after an order is placed. */
const meta = {
  title: "Trust & reassurance",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

/** Below the homepage hero. Only what the site already does - no returns or payment claims yet. */
export const Band: Story = {
  render: () => <TrustStrip className="max-w-6xl" />,
  play: async ({ canvasElement }) => {
    const list = within(canvasElement).getByRole("list", { name: "Our promises" });
    await expect(within(list).getAllByRole("listitem")).toHaveLength(4);
  },
};

/** Beside the buy button on the product page. */
export const Compact: Story = {
  render: () => (
    <div className="max-w-sm">
      <TrustStrip compact />
    </div>
  ),
};

export const PlacedAwaitingPayment: Story = {
  render: () => (
    <div className="max-w-xl space-y-6 text-center">
      <OrderPlacedTick />
      <h1 className="font-display text-3xl">Thank you, your order is placed</h1>
      <div className="text-left">
        <WhatHappensNext awaitingPayment bespoke={false} />
      </div>
    </div>
  ),
};

/** A paid bespoke order: the atelier checks the measurements before cutting. */
export const PlacedBespokePaid: Story = {
  render: () => (
    <div className="max-w-xl">
      <WhatHappensNext awaitingPayment={false} bespoke />
    </div>
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Measured, then stitched")).toBeInTheDocument();
  },
};
