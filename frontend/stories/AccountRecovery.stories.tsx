import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { ForgotPasswordForm } from "@/components/account/ForgotPasswordForm";
import { ResetPasswordForm } from "@/components/account/ResetPasswordForm";
import { VerifyEmail } from "@/components/account/VerifyEmail";

import { mockFetch } from "./mock-fetch";

/** Forgot password, reset from the email link, and email confirmation. */
const meta = {
  title: "Account recovery",
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

/** The same answer whether or not the address has an account. */
export const ForgotPassword: Story = {
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/v1/auth/password/reset/request/",
        status: 202,
        body: { detail: "If that email address matches an account, a message is on its way." },
      },
    ]),
  render: () => <ForgotPasswordForm />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "someone@example.com");
    await userEvent.click(canvas.getByRole("button", { name: "Send the link" }));
    await expect(await canvas.findByText("Check your email")).toBeInTheDocument();
    await expect(canvas.getByText(/If someone@example.com has a Ferasha account/)).toBeInTheDocument();
  },
};

/** A used or expired token offers a fresh link instead of an error code. */
export const ResetLinkExpired: Story = {
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/v1/auth/password/reset/confirm/",
        status: 400,
        body: { token: ["This link is invalid or has expired."] },
      },
    ]),
  render: () => <ResetPasswordForm token="expired-token" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("New password (at least 10 characters)"), "Correct-Horse-9183");
    await userEvent.type(canvas.getByLabelText("Confirm the new password"), "Correct-Horse-9183");
    await userEvent.click(canvas.getByRole("button", { name: "Set new password" }));
    await expect(await canvas.findByRole("link", { name: "Send a new link" })).toHaveAttribute("href", "/account/forgot-password");
  },
};

export const ResetForm: Story = {
  render: () => <ResetPasswordForm token="a-token" />,
};

export const VerifyEmailConfirmed: Story = {
  beforeEach: () =>
    mockFetch([{ method: "POST", path: "/api/v1/auth/email/verify/confirm/", body: { detail: "Email address confirmed." } }]),
  render: () => <VerifyEmail token="a-token" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Confirm my email" }));
    await expect(await canvas.findByText("Email confirmed")).toBeInTheDocument();
  },
};
