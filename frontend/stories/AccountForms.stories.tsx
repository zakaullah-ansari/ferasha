import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { AuthPage } from "@/components/account/AuthCard";
import { RegisterForm } from "@/components/account/RegisterForm";
import { SignInForm } from "@/components/account/SignInForm";

import { mockFetch } from "./mock-fetch";

/**
 * Sign-in and registration: one centred card on a soft brand wash.
 * "Continue with Google" appears only when Django has Google keys; stories
 * show both, since a shop without keys must still look finished. Errors
 * appear when a field is left, clear as soon as they are fixed, and submit
 * moves focus to the first problem.
 */
const meta = {
  title: "Account/Forms",
  parameters: { layout: "fullscreen" },
  decorators: [(Story) => <AuthPage>{Story()}</AuthPage>],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const GOOGLE = [{ id: "google", name: "Google" }] as const;

export const SignIn: Story = { render: () => <SignInForm next="/checkout" providers={GOOGLE} /> };

/** No provider keys configured: no Google button, no "or" divider. */
export const SignInEmailOnly: Story = { render: () => <SignInForm next="/checkout" /> };

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

/** Submitting empty never reaches the server: inline errors, focus on the first. */
export const SignInEmpty: Story = {
  render: () => <SignInForm next="/checkout" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Sign in" }));
    await expect(canvas.getByText("Enter your email address.")).toBeInTheDocument();
    await expect(canvas.getByText("Enter your password.")).toBeInTheDocument();
    await expect(canvas.getByLabelText("Email")).toHaveFocus();
  },
};

/** Back from Google with an email that belongs to a password account. */
export const SignInAfterGoogleConflict: Story = {
  render: () => (
    <SignInForm
      next="/checkout"
      providers={GOOGLE}
      notice={{
        tone: "error",
        message: "An account already uses that email. Sign in with your password (or reset it) to get in.",
      }}
    />
  ),
};

/** The eye shows what was typed, and hides it again on submit. */
export const PasswordVisibility: Story = {
  render: () => <SignInForm next="/checkout" />,
  beforeEach: () =>
    mockFetch([{ method: "POST", path: "/api/session/login", status: 401, body: { detail: "No match." } }]),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const password = canvas.getByLabelText("Password");
    const toggle = canvas.getByRole("button", { name: "Show password" });
    await userEvent.type(password, "Correct-Horse-9182");
    await expect(password).toHaveAttribute("type", "password");

    await userEvent.click(toggle);
    await expect(password).toHaveAttribute("type", "text");
    await expect(toggle).toHaveAttribute("aria-pressed", "true");

    await userEvent.type(canvas.getByLabelText("Email"), "ayesha@example.com");
    await userEvent.click(canvas.getByRole("button", { name: "Sign in" }));
    await expect(password).toHaveAttribute("type", "password");
  },
};

/** Leave "gmial.com" and the fix is one tap away; nothing changes on its own. */
export const EmailTypoSuggestion: Story = {
  render: () => <SignInForm next="/checkout" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const email = canvas.getByLabelText("Email");
    await userEvent.type(email, "ayesha@gmial.com");
    await userEvent.tab();
    await expect(email).toHaveValue("ayesha@gmial.com");
    await userEvent.click(canvas.getByRole("button", { name: "ayesha@gmail.com" }));
    await expect(email).toHaveValue("ayesha@gmail.com");
  },
};

export const Register: Story = { render: () => <RegisterForm next="/checkout" providers={GOOGLE} /> };

export const RegisterEmailOnly: Story = { render: () => <RegisterForm next="/checkout" /> };

/** An error waits until the field is left, then clears the moment it is fixed. */
export const RegisterInlineValidation: Story = {
  render: () => <RegisterForm next="/checkout" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const password = canvas.getByLabelText("Password");
    await userEvent.type(password, "short");
    await expect(canvas.queryByText(/Use at least 10 characters/)).not.toBeInTheDocument();
    await userEvent.tab();
    await userEvent.tab(); // past the eye button
    await expect(canvas.getByText("Use at least 10 characters.")).toBeInTheDocument();
    await userEvent.type(password, "-and-longer");
    await expect(canvas.queryByText("Use at least 10 characters.")).not.toBeInTheDocument();
  },
};

/** Terms are required, and the message says so instead of a greyed-out button. */
export const RegisterTermsRequired: Story = {
  render: () => <RegisterForm next="/checkout" />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Full name"), "Ayesha Khan");
    await userEvent.type(canvas.getByLabelText("Email"), "ayesha@example.com");
    await userEvent.type(canvas.getByLabelText("Password"), "Correct-Horse-9182");
    await userEvent.click(canvas.getByRole("button", { name: "Create account" }));
    await expect(canvas.getByText("Please accept the terms to create an account.")).toBeInTheDocument();
    await expect(canvas.getByRole("checkbox", { name: /accept the terms/ })).toHaveFocus();
  },
};

/** Django's own verdict (here: a breached password) lands under the field. */
export const RegisterBreachedPassword: Story = {
  render: () => <RegisterForm next="/checkout" />,
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/session/register",
        status: 400,
        body: {
          password: [
            "This password has appeared in a data breach elsewhere, so it is easy to guess. Please choose a different one.",
          ],
        },
      },
    ]),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Full name"), "Ayesha Khan");
    await userEvent.type(canvas.getByLabelText("Email"), "ayesha@example.com");
    await userEvent.type(canvas.getByLabelText("Password"), "Summer-2019-pass");
    await userEvent.click(canvas.getByRole("checkbox", { name: /accept the terms/ }));
    await userEvent.click(canvas.getByRole("button", { name: "Create account" }));
    await expect(await canvas.findByText(/appeared in a data breach/)).toBeInTheDocument();
    await expect(canvas.getByLabelText("Password")).toHaveAttribute("aria-invalid", "true");
    await expect(canvas.getByLabelText("Password")).toHaveFocus();
  },
};
