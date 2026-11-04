import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { DashboardSummary } from "@/lib/api/types";
import { attentionItems } from "@/lib/dashboard";
import { formatINR } from "@/lib/format";

import { DashboardCard } from "./DashboardCard";
import { KpiCards } from "./KpiCards";
import { LowStock } from "./LowStock";
import { NeedsYou } from "./NeedsYou";
import { OrdersTable } from "./OrdersTable";
import { PageHeading } from "./PageHeading";
import { Pipeline } from "./Pipeline";
import { RevenueChart } from "./RevenueChart";

const TODAY = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" });

/** The owner's morning: what came in, what waits on them, what is running low. */
export function OverviewView({ summary, today = new Date() }: { summary: DashboardSummary; today?: Date }) {
  const thirtyDays = summary.series.reduce(
    (total, day) => ({ revenue: total.revenue + Number(day.revenue), orders: total.orders + day.orders }),
    { revenue: 0, orders: 0 },
  );

  return (
    <div className="space-y-8">
      <PageHeading eyebrow={TODAY.format(today)} title="Today at the atelier" />

      <KpiCards summary={summary} />

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <DashboardCard
          title="Revenue, last 30 days"
          description={`${formatINR(thirtyDays.revenue)} from ${thirtyDays.orders} paid ${thirtyDays.orders === 1 ? "order" : "orders"}`}
        >
          <RevenueChart series={summary.series} />
        </DashboardCard>
        <DashboardCard title="Needs you" description="Waiting on the atelier, in the order the work happens">
          <NeedsYou items={attentionItems(summary)} />
        </DashboardCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard title="Orders in progress" description="Every open order, by stage">
          <Pipeline pipeline={summary.pipeline} />
        </DashboardCard>
        <DashboardCard id="low-stock" className="scroll-mt-20" title="Running low" description="Sizes with two pieces or fewer">
          <LowStock rows={summary.low_stock} />
        </DashboardCard>
      </div>

      <DashboardCard
        title="Latest orders"
        action={
          <Link href="/dashboard/orders?view=all" className={buttonVariants({ variant: "outline", size: "sm" })}>
            All orders
          </Link>
        }
      >
        {summary.recent_orders.length > 0 ? (
          <OrdersTable orders={summary.recent_orders} caption="Latest orders" />
        ) : (
          <p className="py-6 text-sm text-muted-foreground">No orders yet. They will appear here as they come in.</p>
        )}
      </DashboardCard>
    </div>
  );
}
