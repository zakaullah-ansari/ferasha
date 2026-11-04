import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CheckoutFlow } from "@/components/CheckoutFlow";
import { hasSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Checkout", robots: { index: false } };

export default async function CheckoutPage() {
  // Orders belong to an account. The bag survives sign-in (it lives in the
  // browser), so the customer comes straight back here afterwards.
  if (!(await hasSession())) redirect("/account/sign-in?next=/checkout");

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <h1 className="mb-8 text-center font-display text-display-sm">Checkout</h1>
      <CheckoutFlow />
    </div>
  );
}
