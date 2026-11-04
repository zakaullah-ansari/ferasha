import { CheckCircle2 } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api/client";
import { getAuthed, hasSession } from "@/lib/api/server";
import type { OrderDetail } from "@/lib/api/types";
import { ATELIER } from "@/lib/brand";
import { formatINR } from "@/lib/format";

export const metadata: Metadata = { title: "Your order", robots: { index: false } };

/** Customer-facing wording for the order states a customer can be in. */
const STATUS_LABEL: Record<string, string> = {
  placed: "Awaiting payment",
  payment_confirmed: "Payment received",
  in_atelier: "In the atelier",
  measurement_review: "Reviewing measurements",
  stitching: "Being stitched",
  quality_check: "Final quality check",
  packed: "Packed",
  shipped: "On its way",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

async function loadOrder(orderNumber: string): Promise<OrderDetail> {
  try {
    return await getAuthed<OrderDetail>(`/api/v1/orders/${encodeURIComponent(orderNumber)}/`);
  } catch (error) {
    // Another customer's order 404s exactly like a missing one.
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && error.status === 401) {
      redirect(`/account/sign-in?next=/orders/${encodeURIComponent(orderNumber)}`);
    }
    throw error;
  }
}

export default async function OrderPage({
  params,
  searchParams,
}: {
  params: Promise<{ orderNumber: string }>;
  searchParams: Promise<{ placed?: string }>;
}) {
  const { orderNumber } = await params;
  if (!(await hasSession())) {
    redirect(`/account/sign-in?next=/orders/${encodeURIComponent(orderNumber)}`);
  }
  const order = await loadOrder(orderNumber);
  const justPlaced = (await searchParams).placed === "1";
  const address = order.shipping_address;
  const tax = order.tax_snapshot;

  return (
    <div className="mx-auto max-w-2xl space-y-8 px-5 py-12">
      <header className="space-y-3 text-center">
        {justPlaced && <CheckCircle2 className="mx-auto size-10 text-primary" aria-hidden="true" />}
        <h1 className="font-display text-display-sm">
          {justPlaced ? "Thank you, your order is placed" : `Order ${order.order_number}`}
        </h1>
        <p className="text-muted-foreground">
          Order <span className="font-medium text-foreground">{order.order_number}</span>
        </p>
        <Badge variant="secondary">{STATUS_LABEL[order.status] ?? order.status}</Badge>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Items</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <ul className="divide-y">
            {order.lines.map((line) => (
              <li key={line.id} className="flex justify-between gap-4 py-3 text-sm">
                <span>
                  {line.product_name}
                  <span className="block text-muted-foreground">
                    {line.variant_label} · Qty {line.quantity}
                  </span>
                </span>
                <span className="tabular-nums">{formatINR(line.gross)}</span>
              </li>
            ))}
          </ul>

          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted-foreground">Subtotal</dt>
            <dd className="tabular-nums">{formatINR(order.subtotal)}</dd>
            <dt className="text-muted-foreground">Delivery</dt>
            <dd className="tabular-nums">
              {Number(order.shipping_charge) === 0 ? "Free" : formatINR(order.shipping_charge)}
            </dd>
            {tax && order.supply_type === "intra_state" && (
              <>
                <dt className="text-muted-foreground">CGST</dt>
                <dd className="tabular-nums">{formatINR(tax.cgst_total)}</dd>
                <dt className="text-muted-foreground">SGST</dt>
                <dd className="tabular-nums">{formatINR(tax.sgst_total)}</dd>
              </>
            )}
            {tax && order.supply_type === "inter_state" && (
              <>
                <dt className="text-muted-foreground">IGST</dt>
                <dd className="tabular-nums">{formatINR(tax.igst_total)}</dd>
              </>
            )}
            <dt className="border-t pt-3 font-medium">Total</dt>
            <dd className="border-t pt-3 font-heading text-2xl tabular-nums">
              {formatINR(order.grand_total)}
            </dd>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Delivering to</CardTitle>
        </CardHeader>
        <CardContent>
          <address className="text-sm not-italic leading-relaxed">
            {address.recipient_name}
            <br />
            {address.line1}
            {address.line2 && (
              <>
                <br />
                {address.line2}
              </>
            )}
            <br />
            {address.city} {address.state_code} {address.postal_code}
            <br />
            {address.phone}
          </address>
        </CardContent>
      </Card>

      <p className="text-center text-sm text-muted-foreground">
        Questions about your order? Call {ATELIER.name} on{" "}
        <a href={ATELIER.phoneHref} className="text-foreground underline underline-offset-4">
          {ATELIER.phoneDisplay}
        </a>
        .
      </p>
      <div className="text-center">
        <Link href="/products" className={buttonVariants({ variant: "outline" })}>
          Continue shopping
        </Link>
      </div>
    </div>
  );
}
