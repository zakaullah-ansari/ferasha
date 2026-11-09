import { Search } from "lucide-react";
import Link from "next/link";

import { LinkPagination } from "@/components/LinkPagination";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ADMIN_LINKS } from "@/lib/admin-links";
import type { OrderSummary } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { ordersHref } from "@/lib/dashboard";
import { ORDER_VIEWS, type OrderView } from "@/lib/order-status";

import { OrdersTable } from "./OrdersTable";
import { PageHeading } from "./PageHeading";

interface OrdersListViewProps {
  readonly view: OrderView;
  readonly q?: string;
  readonly page: number;
  readonly pageCount: number;
  readonly count: number;
  readonly orders: readonly OrderSummary[];
}

/**
 * Orders by stage. Tabs, search and pages are plain links and a GET form, so
 * the URL says what is on screen and every view can be bookmarked.
 */
export function OrdersListView({ view, q, page, pageCount, count, orders }: OrdersListViewProps) {
  return (
    <div className="space-y-6">
      <PageHeading eyebrow="Orders" title={view.label}>
        <a href={ADMIN_LINKS.order(q ?? "")} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "outline" })}>
          Open in Django admin
        </a>
      </PageHeading>

      <nav aria-label="Order stages" className="-mx-4 overflow-x-auto px-4">
        <ul className="flex w-max gap-1">
          {ORDER_VIEWS.map((candidate) => (
            <li key={candidate.id}>
              <Link
                href={ordersHref({ view: candidate.id, q })}
                aria-current={candidate.id === view.id ? "page" : undefined}
                className={cn(buttonVariants({ variant: candidate.id === view.id ? "secondary" : "ghost", size: "sm" }))}
              >
                {candidate.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <form action="/dashboard/orders" role="search" className="flex max-w-md gap-2">
        <input type="hidden" name="view" value={view.id} />
        <Input
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Order number, name or email"
          aria-label="Search orders"
        />
        <Button type="submit" variant="outline">
          <Search data-icon="inline-start" />
          Search
        </Button>
      </form>

      <Card>
        <CardContent>
          <p aria-live="polite" className="pb-2 text-sm text-muted-foreground">
            {count} {count === 1 ? "order" : "orders"}
            {q && ` matching “${q}”`}
          </p>
          {orders.length > 0 ? (
            <OrdersTable orders={orders} caption={`${view.label} orders`} />
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">
              {q ? "No orders match that search here. Try All." : "Nothing at this stage."}
            </p>
          )}
        </CardContent>
      </Card>

      <LinkPagination page={page} pageCount={pageCount} href={(target) => ordersHref({ view: view.id, q, page: target })} />
    </div>
  );
}
