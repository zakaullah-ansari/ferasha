import { redirect } from "next/navigation";

import { OrdersListView } from "@/components/dashboard/OrdersListView";
import { ApiError } from "@/lib/api/client";
import type { OrderSummary, Paginated } from "@/lib/api/types";
import { getBackOffice } from "@/lib/back-office";
import { ordersHref } from "@/lib/dashboard";
import { orderView } from "@/lib/order-status";
import { pageCount } from "@/lib/pagination";

export const metadata = { title: "Orders" };

type Params = Readonly<Record<string, string | string[] | undefined>>;

const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value)?.trim() || undefined;

export default async function OrdersPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const view = orderView(first(params.view));
  const q = first(params.q);
  const requested = Number.parseInt(first(params.page) ?? "", 10);
  const page = Number.isSafeInteger(requested) && requested > 1 ? requested : 1;

  const query = new URLSearchParams();
  for (const status of view.statuses) query.append("status", status);
  if (q) query.set("search", q);
  if (page > 1) query.set("page", String(page));

  let data: Paginated<OrderSummary>;
  try {
    data = await getBackOffice<Paginated<OrderSummary>>(`/api/v1/orders/?${query}`);
  } catch (error) {
    // A page past the end (orders moved on since the link was made): back to the first.
    if (error instanceof ApiError && error.status === 404 && page > 1) redirect(ordersHref({ view: view.id, q }));
    throw error;
  }

  return (
    <OrdersListView
      view={view}
      q={q}
      page={page}
      pageCount={pageCount(data.count)}
      count={data.count}
      orders={data.results}
    />
  );
}
