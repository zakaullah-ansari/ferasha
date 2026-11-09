import { getRouter } from "@storybook/nextjs-vite/navigation.mock";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";

import { AccountView } from "@/components/account/AccountView";

import { RECENT_ORDERS } from "../tests/fixtures/back-office";
import { CUSTOMER } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** The customer's account page (/account): orders, details, password. */
const meta = {
  title: "Account page",
  parameters: { layout: "fullscreen", nextjs: { navigation: { pathname: "/account" } } },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const AYESHA = { ...CUSTOMER, phone: "+919820012345" };

export const WithOrders: Story = {
  render: () => <AccountView user={AYESHA} orders={RECENT_ORDERS} page={1} pageCount={2} />,
};

export const NoOrdersYet: Story = {
  render: () => <AccountView user={AYESHA} orders={[]} page={1} pageCount={0} />,
};

export const SavesDetails: Story = {
  beforeEach: () => mockFetch([{ method: "PATCH", path: "/api/v1/auth/me/", body: { ...AYESHA, full_name: "Ayesha K. Khan" } }]),
  render: () => <AccountView user={AYESHA} orders={[]} page={1} pageCount={0} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const name = canvas.getByLabelText("Full name");
    await userEvent.clear(name);
    await userEvent.type(name, "Ayesha K. Khan");
    await userEvent.click(canvas.getByRole("button", { name: "Save details" }));
    await expect(await canvas.findByText("Saved.")).toBeInTheDocument();
    await waitFor(() => expect(getRouter().refresh).toHaveBeenCalled());
  },
};

/** A wrong current password is shown against that field; nobody is signed out. */
export const PasswordRefused: Story = {
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/v1/auth/password/change/",
        status: 400,
        body: { current_password: ["Your current password is incorrect."] },
      },
    ]),
  render: () => <AccountView user={AYESHA} orders={[]} page={1} pageCount={0} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Current password"), "not-my-password");
    await userEvent.type(canvas.getByLabelText("New password (at least 10 characters)"), "Correct-Horse-9183");
    await userEvent.type(canvas.getByLabelText("Confirm the new password"), "Correct-Horse-9183");
    await userEvent.click(canvas.getByRole("button", { name: "Change password" }));
    await expect(await canvas.findByText("Your current password is incorrect.")).toBeInTheDocument();
    await expect(getRouter().replace).not.toHaveBeenCalled();
  },
};
