import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { FitDrawer } from "@/components/FitDrawer";

const meta = {
  title: "Commerce/FitDrawer",
  component: FitDrawer,
  parameters: { layout: "fullscreen" },
  args: {
    open: true,
    onClose: fn(),
    onSubmit: fn(),
    garment: "suit_set",
    productName: "Karachi Lawn Chikankari - Ivory",
    supportsBespoke: true,
    sizes: ["S", "M", "L"],
  },
} satisfies Meta<typeof FitDrawer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const StandardSizes: Story = {};

export const NoBespoke: Story = { args: { supportsBespoke: false } };

/** Measurements in canonical inches, validated against the backend contract. */
export const Bespoke: Story = {
  play: async ({ canvasElement }) => {
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(page.getByRole("tab", { name: /bespoke/i }));
    await expect(page.getByRole("button", { name: "Save measurements" })).toBeInTheDocument();
  },
};
