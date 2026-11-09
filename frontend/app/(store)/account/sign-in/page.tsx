import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SignInForm } from "@/components/account/SignInForm";
import { hasSession, safeNextPath } from "@/lib/api/server";

export const metadata: Metadata = { title: "Sign in", robots: { index: false } };

const NOTICES = {
  "password-changed": "Your password has been changed. Please sign in with the new one.",
  "password-reset": "Your password has been reset. Please sign in with the new one.",
} as const;

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
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <SignInForm next={next} notice={notice} />
    </div>
  );
}
