import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SignInForm } from "@/components/account/SignInForm";
import { hasSession, safeNextPath } from "@/lib/api/server";

export const metadata: Metadata = { title: "Sign in", robots: { index: false } };

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const next = safeNextPath((await searchParams).next);
  if (await hasSession()) redirect(next);
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <SignInForm next={next} />
    </div>
  );
}
