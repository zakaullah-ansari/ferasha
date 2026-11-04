import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardSummary } from "@/lib/api/types";
import { change } from "@/lib/dashboard";
import { formatINR } from "@/lib/format";

function Delta({ current, previous }: { current: number; previous: number }) {
  const delta = change(current, previous);
  if (!delta) return <p className="text-xs text-muted-foreground">Nothing to compare with last month yet</p>;
  const Icon = delta.direction === "up" ? TrendingUp : delta.direction === "down" ? TrendingDown : Minus;
  const words =
    delta.direction === "flat" ? "Level" : `${delta.direction === "up" ? "Up" : "Down"} ${delta.percent}%`;
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <Icon aria-hidden="true" className={delta.direction === "up" ? "size-4 text-primary" : "size-4"} />
      <span>{words} vs the same days last month</span>
    </p>
  );
}

function Figure({ label, value, children }: { label: string; value: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-display text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

/** This month so far, each figure against the same span of last month. Paid orders only. */
export function KpiCards({ summary }: { summary: DashboardSummary }) {
  const { revenue, orders, average_order_value } = summary;
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Figure label="Revenue this month" value={formatINR(revenue.month_to_date)}>
        <Delta current={Number(revenue.month_to_date)} previous={Number(revenue.previous_period)} />
      </Figure>
      <Figure label="Paid orders this month" value={String(orders.month_to_date)}>
        <Delta current={orders.month_to_date} previous={orders.previous_period} />
      </Figure>
      <Figure label="Average paid order" value={average_order_value ? formatINR(average_order_value) : "—"}>
        <p className="text-xs text-muted-foreground">Including GST and delivery</p>
      </Figure>
    </div>
  );
}
