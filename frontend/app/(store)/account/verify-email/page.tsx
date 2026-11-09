import type { Metadata } from "next";

import { VerifyEmail } from "@/components/account/VerifyEmail";

// The token is a credential: keep the page out of search and its URL out of referrers.
export const metadata: Metadata = { title: "Confirm your email", robots: { index: false }, referrer: "no-referrer" };

export default async function VerifyEmailPage({ searchParams }: { searchParams: Promise<{ token?: string | string[] }> }) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <VerifyEmail token={(Array.isArray(token) ? token[0] : token) ?? ""} />
    </div>
  );
}
