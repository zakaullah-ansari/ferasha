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

/** Email not yet confirmed: a quiet nudge with a one-tap resend. */
export const EmailNotConfirmed: Story = {
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: "/api/v1/auth/email/verify/request/", body: { detail: "If that account exists, a link is on its way." } },
    ]),
  render: () => <AccountView user={{ ...AYESHA, email_verified: false }} orders={[]} page={1} pageCount={0} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Please confirm your email.")).toBeInTheDocument();
    await userEvent.click(canvas.getByRole("button", { name: "Send a new link" }));
    await expect(await canvas.findByText("Sent. Check your inbox.")).toBeInTheDocument();
  },
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

/** "Your data": download everything, or delete the account with the password. */
export const DeletesAccount: Story = {
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: "/api/v1/auth/me/delete/", body: { detail: "Your account has been deleted." } },
      { method: "POST", path: "/api/session/logout", status: 204 },
    ]),
  render: () => <AccountView user={AYESHA} orders={[]} page={1} pageCount={0} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("link", { name: "Download my data" })).toHaveAttribute("href", "/api/v1/auth/me/export/");
    await userEvent.click(canvas.getByRole("button", { name: "Delete my account" }));
    // The dialog renders in a portal, outside the story's canvas.
    const dialog = within(await within(document.body).findByRole("dialog"));
    const confirm = dialog.getByRole("button", { name: "Delete my account" });
    await expect(confirm).toBeDisabled();
    await userEvent.type(dialog.getByLabelText("Your password, to confirm it's you"), "Correct-Horse-9182");
    await userEvent.click(confirm);
    await waitFor(() => expect(getRouter().replace).toHaveBeenCalledWith("/account/sign-in?reason=account-deleted"));
  },
};

/** An order still being made: the account waits, and the order is named. */
export const DeleteWaitsForOrders: Story = {
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/v1/auth/me/delete/",
        status: 409,
        body: {
          detail: "You have orders still in progress (FER-24-0193). Your account can be deleted once they have been delivered or cancelled.",
          order_numbers: ["FER-24-0193"],
        },
      },
    ]),
  render: () => <AccountView user={AYESHA} orders={[]} page={1} pageCount={0} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Delete my account" }));
    const dialog = within(await within(document.body).findByRole("dialog"));
    await userEvent.type(dialog.getByLabelText("Your password, to confirm it's you"), "Correct-Horse-9182");
    await userEvent.click(dialog.getByRole("button", { name: "Delete my account" }));
    await expect(await dialog.findByRole("alert")).toHaveTextContent("FER-24-0193");
    await expect(getRouter().replace).not.toHaveBeenCalled();
  },
};
