import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import type { OrderSummary } from "@/lib/api/types";
import { formatINR, formatMoment } from "@/lib/format";
import { orderStatus } from "@/lib/order-status";

/** A customer's orders, newest first; each opens its own page with the full timeline. */
export function OrderHistory({ orders }: { orders: readonly OrderSummary[] }) {
  if (orders.length === 0) {
    return (
      <div className="flex flex-col items-start gap-4 py-6">
        <p className="text-sm text-muted-foreground">No orders yet. When you place one, you can follow it here.</p>
        <Link href="/products" className={buttonVariants({ variant: "outline" })}>
          Explore the collection
        </Link>
      </div>
    );
  }
  return (
    <ul className="divide-y">
      {orders.map((order) => (
        <li key={order.id}>
          <Link
            href={`/orders/${encodeURIComponent(order.order_number)}`}
            className="group grid grid-cols-[1fr_auto_auto] items-center gap-x-4 gap-y-1 py-4"
          >
            <span className="min-w-0 truncate font-medium group-hover:underline">
              {order.item_summary || order.order_number}
            </span>
            <span className="text-right tabular-nums">{formatINR(order.grand_total)}</span>
            <ChevronRight aria-hidden="true" className="row-span-2 size-4 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {order.order_number} · {formatMoment(order.placed_at)}
            </span>
            <Badge variant="secondary" className="justify-self-end">
              {orderStatus(order.status).customer}
            </Badge>
          </Link>
        </li>
      ))}
    </ul>
  );
}
