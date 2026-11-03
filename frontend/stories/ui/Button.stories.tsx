import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { ShoppingBag } from "lucide-react";

import { Button } from "@/components/ui/button";

const meta = {
  title: "UI/Button",
  component: Button,
  tags: ["autodocs"],
  parameters: { layout: "centered" },
  args: { children: "Add to bag" },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};
export const Outline: Story = { args: { variant: "outline", children: "Select your fit" } };
export const Ghost: Story = { args: { variant: "ghost", children: "Sign out" } };
export const Large: Story = { args: { size: "lg", children: "Place order · ₹14,160" } };
export const Disabled: Story = { args: { disabled: true } };
export const Icon: Story = {
  args: { variant: "ghost", size: "icon", "aria-label": "Open bag", children: <ShoppingBag /> },
};
