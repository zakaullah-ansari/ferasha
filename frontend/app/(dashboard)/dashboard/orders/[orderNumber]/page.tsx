import { notFound } from "next/navigation";

import { OrderDetailView } from "@/components/dashboard/OrderDetailView";
import { ApiError } from "@/lib/api/client";
import type { OrderDetail } from "@/lib/api/types";
import { getBackOffice } from "@/lib/back-office";

type Props = { params: Promise<{ orderNumber: string }> };

export async function generateMetadata({ params }: Props) {
  return { title: (await params).orderNumber };
}

export default async function DashboardOrderPage({ params }: Props) {
  const { orderNumber } = await params;
  let order: OrderDetail;
  try {
    order = await getBackOffice<OrderDetail>(`/api/v1/orders/${encodeURIComponent(orderNumber)}/`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  return <OrderDetailView order={order} />;
}
