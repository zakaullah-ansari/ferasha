import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthPage, type AuthNotice } from "@/components/account/AuthCard";
import { SignInForm } from "@/components/account/SignInForm";
import { getSocialProviders, hasSession, safeNextPath } from "@/lib/api/server";

export const metadata: Metadata = { title: "Sign in", robots: { index: false } };

const NOTICES = {
  "password-changed": { tone: "info", message: "Your password has been changed. Please sign in with the new one." },
  "password-reset": { tone: "info", message: "Your password has been reset. Please sign in with the new one." },
  "oauth-cancelled": { tone: "info", message: "Sign-in was cancelled. Try again, or use your email below." },
  "oauth-failed": {
    tone: "error",
    message: "We couldn't complete that sign-in. Please try again, or use your email below.",
  },
  "oauth-conflict": {
    tone: "error",
    message:
      "An account already uses that email. Sign in with your password (or reset it) to get in.",
  },
  "oauth-forbidden": {
    tone: "error",
    message: "That account can't sign in this way. Please use your email and password.",
  },
} as const satisfies Record<string, AuthNotice>;

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[]; reason?: string | string[] }>;
}) {
  const params = await searchParams;
  const next = safeNextPath(params.next);
  // Fixed wording per reason: nothing from the URL is ever shown as text.
  const reason = Array.isArray(params.reason) ? params.reason[0] : params.reason;
  const notice = reason && Object.hasOwn(NOTICES, reason) ? NOTICES[reason as keyof typeof NOTICES] : undefined;
  if (await hasSession()) redirect(next);
  const providers = await getSocialProviders();
  return (
    <AuthPage>
      <SignInForm next={next} notice={notice} providers={providers} />
    </AuthPage>
  );
}
