import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { RegisterForm } from "@/components/account/RegisterForm";
import { hasSession, safeNextPath } from "@/lib/api/server";

export const metadata: Metadata = { title: "Create an account", robots: { index: false } };

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const next = safeNextPath((await searchParams).next);
  if (await hasSession()) redirect(next);
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <RegisterForm next={next} />
    </div>
  );
}
