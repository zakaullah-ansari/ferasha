import Link from "next/link";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { OrderSummary } from "@/lib/api/types";
import { formatMoment } from "@/lib/dashboard";
import { formatINR } from "@/lib/format";

import { OrderStatusBadge } from "./OrderStatusBadge";

/** Orders as rows; the order number opens the order. Narrow screens keep number, customer, total and stage. */
export function OrdersTable({ orders, caption }: { orders: readonly OrderSummary[]; caption: string }) {
  return (
    <Table>
      <TableCaption className="sr-only">{caption}</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Order</TableHead>
          <TableHead>Customer</TableHead>
          <TableHead className="hidden md:table-cell">Placed</TableHead>
          <TableHead className="hidden text-right sm:table-cell">Items</TableHead>
          <TableHead className="text-right">Total</TableHead>
          <TableHead>Stage</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map((order) => (
          <TableRow key={order.id}>
            <TableCell>
              <Link
                href={`/dashboard/orders/${encodeURIComponent(order.order_number)}`}
                className="font-medium tabular-nums underline-offset-4 hover:underline"
              >
                {order.order_number}
              </Link>
            </TableCell>
            <TableCell className="max-w-40 truncate">{order.customer_name}</TableCell>
            <TableCell className="hidden text-muted-foreground md:table-cell">{formatMoment(order.placed_at)}</TableCell>
            <TableCell className="hidden text-right tabular-nums sm:table-cell">{order.line_count}</TableCell>
            <TableCell className="text-right tabular-nums">{formatINR(order.grand_total)}</TableCell>
            <TableCell>
              <OrderStatusBadge status={order.status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
