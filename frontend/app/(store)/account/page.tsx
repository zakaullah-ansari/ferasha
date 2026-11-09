import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AccountView } from "@/components/account/AccountView";
import { ApiError } from "@/lib/api/client";
import { getSignedIn, requireSession } from "@/lib/api/server";
import type { OrderSummary, Paginated } from "@/lib/api/types";
import { pageCount } from "@/lib/pagination";

export const metadata: Metadata = { title: "Your account", robots: { index: false } };

export default async function AccountPage({ searchParams }: { searchParams: Promise<{ page?: string | string[] }> }) {
  const user = await requireSession("/account");
  const raw = (await searchParams).page;
  const requested = Number.parseInt(Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? ""), 10);
  const page = Number.isSafeInteger(requested) && requested > 1 ? requested : 1;

  let orders: Paginated<OrderSummary>;
  try {
    orders = await getSignedIn<Paginated<OrderSummary>>(`/api/v1/orders/?mine=true${page > 1 ? `&page=${page}` : ""}`, "/account");
  } catch (error) {
    // A page past the end: back to the first.
    if (error instanceof ApiError && error.status === 404 && page > 1) redirect("/account");
    throw error;
  }

  return <AccountView user={user} orders={orders.results} page={page} pageCount={pageCount(orders.count)} />;
}
