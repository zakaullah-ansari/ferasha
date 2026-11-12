import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthPage } from "@/components/account/AuthCard";
import { RegisterForm } from "@/components/account/RegisterForm";
import { getSocialProviders, hasSession, safeNextPath } from "@/lib/api/server";

export const metadata: Metadata = { title: "Create an account", robots: { index: false } };

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const next = safeNextPath((await searchParams).next);
  if (await hasSession()) redirect(next);
  const providers = await getSocialProviders();
  return (
    <AuthPage>
      <RegisterForm next={next} providers={providers} />
    </AuthPage>
  );
}
