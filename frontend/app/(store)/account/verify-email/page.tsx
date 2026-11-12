import type { Metadata } from "next";

import { VerifyEmail } from "@/components/account/VerifyEmail";
import { AuthPage } from "@/components/account/AuthCard";

// The token is a credential: keep the page out of search and its URL out of referrers.
export const metadata: Metadata = { title: "Confirm your email", robots: { index: false }, referrer: "no-referrer" };

export default async function VerifyEmailPage({ searchParams }: { searchParams: Promise<{ token?: string | string[] }> }) {
  const { token } = await searchParams;
  return (
    <AuthPage>
      <VerifyEmail token={(Array.isArray(token) ? token[0] : token) ?? ""} />
    </AuthPage>
  );
}
