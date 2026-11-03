import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { HeaderActions } from "@/components/HeaderActions";
import { useCartStore } from "@/store/useCartStore";

import { BAG, CUSTOMER } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** Header island: account state (fetched) and the bag count. */
const meta = {
  title: "Commerce/HeaderActions",
  component: HeaderActions,
  parameters: { layout: "centered" },
} satisfies Meta<typeof HeaderActions>;

export default meta;
type Story = StoryObj<typeof meta>;

const ME = "/api/v1/auth/me/";

function scenario(signedIn: boolean, items: typeof BAG) {
  return () => {
    useCartStore.setState({ items, isOpen: false });
    const restore = mockFetch([
      signedIn ? { path: ME, body: CUSTOMER } : { path: ME, status: 401, body: { detail: "Not signed in" } },
    ]);
    return () => {
      restore();
      useCartStore.setState({ items: [], isOpen: false });
    };
  };
}

export const Guest: Story = { beforeEach: scenario(false, []) };
export const GuestWithBag: Story = { beforeEach: scenario(false, BAG) };
export const SignedIn: Story = { beforeEach: scenario(true, BAG) };
