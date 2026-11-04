"use client";

import { useId } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { DashboardSummary } from "@/lib/api/types";
import { formatDay } from "@/lib/dashboard";
import { formatINR, formatINRCompact } from "@/lib/format";

// Primary, not --chart-1: the line must hold its contrast against the card.
const CONFIG = { revenue: { label: "Revenue", color: "var(--primary)" } } satisfies ChartConfig;

/** Paid revenue per day for the last thirty days. Quiet days are drawn as zero, not skipped. */
export function RevenueChart({ series }: { series: DashboardSummary["series"] }) {
  const fill = `revenue-fill-${useId().replace(/:/g, "")}`;
  const data = series.map((day) => ({ date: day.date, revenue: Number(day.revenue), orders: day.orders }));

  // A flat line on a ₹0–₹4 axis says nothing; say it in words instead.
  if (data.every((day) => day.revenue === 0)) {
    return (
      <div className="flex h-60 items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
        No paid orders in the last 30 days
      </div>
    );
  }

  return (
    <ChartContainer config={CONFIG} className="aspect-auto h-60 w-full">
      <AreaChart data={data} margin={{ top: 8, left: 4, right: 8 }} accessibilityLayer>
        <defs>
          <linearGradient id={fill} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-revenue)" stopOpacity={0.25} />
            <stop offset="95%" stopColor="var(--color-revenue)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} minTickGap={28} tickFormatter={formatDay} />
        <YAxis tickLine={false} axisLine={false} width={56} tickFormatter={formatINRCompact} />
        <ChartTooltip
          cursor={false}
          content={
            <ChartTooltipContent
              indicator="line"
              labelFormatter={(_, payload) => formatDay(String(payload[0]?.payload.date ?? ""))}
              formatter={(value, _name, item) => (
                <div className="flex w-full items-baseline justify-between gap-6">
                  <span className="text-muted-foreground">
                    {item.payload.orders} {item.payload.orders === 1 ? "order" : "orders"}
                  </span>
                  <span className="font-medium tabular-nums">{formatINR(Number(value))}</span>
                </div>
              )}
            />
          }
        />
        <Area dataKey="revenue" type="monotone" stroke="var(--color-revenue)" strokeWidth={2} fill={`url(#${fill})`} />
      </AreaChart>
    </ChartContainer>
  );
}
