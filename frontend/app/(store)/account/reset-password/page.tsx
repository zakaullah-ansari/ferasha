import type { Metadata } from "next";

import { ResetPasswordForm } from "@/components/account/ResetPasswordForm";

// The token is a credential: keep the page out of search and its URL out of referrers.
export const metadata: Metadata = { title: "Choose a new password", robots: { index: false }, referrer: "no-referrer" };

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string | string[] }> }) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <ResetPasswordForm token={(Array.isArray(token) ? token[0] : token) ?? ""} />
    </div>
  );
}
