import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { RegisterForm } from "@/components/account/RegisterForm";
import { SignInForm } from "@/components/account/SignInForm";

import { mockFetch } from "./mock-fetch";

/** Sign-in and registration. The session itself lives in httpOnly cookies. */
const meta = {
  title: "Account/Forms",
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const SignIn: Story = { render: () => <SignInForm next="/checkout" /> };

export const SignInWrongPassword: Story = {
  render: () => <SignInForm next="/checkout" />,
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/session/login",
        status: 401,
        body: { detail: "That email and password don't match an account." },
      },
    ]),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "ayesha@example.com");
    await userEvent.type(canvas.getByLabelText("Password"), "not-my-password");
    await userEvent.click(canvas.getByRole("button", { name: "Sign in" }));
    await expect(await canvas.findByRole("alert")).toHaveTextContent("don't match an account");
  },
};

export const Register: Story = { render: () => <RegisterForm next="/checkout" /> };

/** Django's own validation message lands under the field that caused it. */
export const RegisterPasswordsDiffer: Story = {
  render: () => <RegisterForm next="/checkout" />,
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/session/register",
        status: 400,
        body: { password_confirm: ["Passwords do not match."] },
      },
    ]),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Full name"), "Ayesha Khan");
    await userEvent.type(canvas.getByLabelText("Email"), "ayesha@example.com");
    await userEvent.type(canvas.getByLabelText("Password (at least 10 characters)"), "Correct-Horse-9182");
    await userEvent.type(canvas.getByLabelText("Confirm password"), "Different-Horse-0000");
    await userEvent.click(canvas.getByRole("checkbox", { name: /accept the terms/ }));
    await userEvent.click(canvas.getByRole("button", { name: "Create account" }));
    await expect(await canvas.findByText("Passwords do not match.")).toBeInTheDocument();
  },
};
