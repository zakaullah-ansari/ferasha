import { ArrowUpRight, Mail, Phone } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ADMIN_LINKS } from "@/lib/admin-links";
import type { OrderDetail } from "@/lib/api/types";
import { formatMoment } from "@/lib/dashboard";
import { formatINR } from "@/lib/format";
import { orderStatus } from "@/lib/order-status";

import { DashboardCard } from "./DashboardCard";
import { OrderActions } from "./OrderActions";
import { OrderStatusBadge } from "./OrderStatusBadge";
import { PageHeading } from "./PageHeading";

function Totals({ order }: { order: OrderDetail }) {
  const rows: [string, string][] = [
    ["Subtotal", order.subtotal],
    ["Delivery", order.shipping_charge],
    ["GST", order.tax_total],
  ];
  return (
    <dl className="ml-auto grid w-full max-w-xs grid-cols-[1fr_auto] gap-x-6 gap-y-1 pt-4 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="text-right tabular-nums">{formatINR(value)}</dd>
        </div>
      ))}
      <dt className="border-t pt-2 font-medium">Total</dt>
      <dd className="border-t pt-2 text-right font-medium tabular-nums">{formatINR(order.grand_total)}</dd>
    </dl>
  );
}

function Lines({ order }: { order: OrderDetail }) {
  return (
    <>
      <Table>
        <TableCaption className="sr-only">Garments in this order</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead>Garment</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Amount</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {order.lines.map((line) => (
            <TableRow key={line.id}>
              <TableCell className="whitespace-normal">
                <span className="flex flex-wrap items-center gap-2">
                  {line.product_name}
                  {line.is_bespoke && <Badge>Bespoke</Badge>}
                </span>
                <span className="text-xs text-muted-foreground">
                  {line.variant_label} · {line.sku}
                </span>
              </TableCell>
              <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
              <TableCell className="text-right tabular-nums">{formatINR(line.gross)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Totals order={order} />
    </>
  );
}

function Timeline({ events }: { events: OrderDetail["events"] }) {
  return (
    <ol className="space-y-4">
      {events.map((event) => (
        <li key={event.id} className="grid grid-cols-[auto_1fr] gap-x-3">
          <span aria-hidden="true" className="mt-1.5 size-2 rounded-full bg-primary" />
          <div className="text-sm">
            <p className="font-medium">{orderStatus(event.to_status).label}</p>
            <p className="text-xs text-muted-foreground">
              {formatMoment(event.created_at)}
              {event.actor_name && ` · ${event.actor_name}`}
            </p>
            {event.reason && <p className="mt-1 text-muted-foreground">“{event.reason}”</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}

function Customer({ order }: { order: OrderDetail }) {
  const address = order.shipping_address;
  return (
    <div className="space-y-4 text-sm">
      <div className="space-y-2">
        {order.contact_email && (
          <a href={`mailto:${order.contact_email}`} className="flex items-center gap-2 break-all hover:text-primary">
            <Mail aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
            {order.contact_email}
          </a>
        )}
        {address.phone && (
          <a href={`tel:${address.phone}`} className="flex items-center gap-2 hover:text-primary">
            <Phone aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
            {address.phone}
          </a>
        )}
      </div>
      <address className="leading-relaxed text-muted-foreground not-italic">
        <span className="block text-foreground">{address.recipient_name}</span>
        {address.line1}
        {address.line2 && <>, {address.line2}</>}
        <br />
        {address.city}, {address.state_code} {address.postal_code}
      </address>
    </div>
  );
}

/** One order, for the atelier: what to make, for whom, where it has been, and what to do next. */
export function OrderDetailView({ order }: { order: OrderDetail }) {
  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="text-sm">
        <Link href="/dashboard/orders" className="text-muted-foreground hover:text-foreground">
          ← Orders
        </Link>
      </nav>

      <PageHeading eyebrow={`Placed ${formatMoment(order.placed_at)}`} title={order.order_number}>
        <a href={ADMIN_LINKS.order(order.order_number)} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "outline" })}>
          Open in Django admin
          <ArrowUpRight data-icon="inline-end" />
        </a>
      </PageHeading>

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-4">
          <DashboardCard title="What to make">
            <Lines order={order} />
          </DashboardCard>
          {order.customer_notes && (
            <DashboardCard title="The customer’s note">
              <blockquote className="border-l-2 border-primary pl-4 text-sm leading-relaxed">{order.customer_notes}</blockquote>
            </DashboardCard>
          )}
          <DashboardCard title="Timeline">
            <Timeline events={order.events} />
          </DashboardCard>
        </div>

        <div className="min-w-0 space-y-4 lg:sticky lg:top-20 lg:self-start">
          <DashboardCard title="Next step" action={<OrderStatusBadge status={order.status} />}>
            <OrderActions order={order} />
          </DashboardCard>
          <DashboardCard title={order.customer_name}>
            <Customer order={order} />
          </DashboardCard>
        </div>
      </div>
    </div>
  );
}
