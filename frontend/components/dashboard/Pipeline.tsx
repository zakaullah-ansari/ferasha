import Link from "next/link";

import type { DashboardSummary } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { waitsOnAtelier } from "@/lib/dashboard";
import { ORDER_VIEWS, orderStatus } from "@/lib/order-status";

/** Every open stage with its count as a bar; stages waiting on the atelier are drawn in green. */
export function Pipeline({ pipeline }: { pipeline: DashboardSummary["pipeline"] }) {
  const most = Math.max(1, ...pipeline.map((stage) => stage.count));
  return (
    <ul className="space-y-3">
      {pipeline.map(({ status, count }) => {
        const view = ORDER_VIEWS.find((candidate) => candidate.statuses.includes(status))?.id ?? "all";
        return (
          <li key={status}>
            <Link
              href={`/dashboard/orders?view=${view}`}
              className="grid grid-cols-[9.5rem_1fr_2rem] items-center gap-3 text-sm hover:text-primary"
            >
              <span className="truncate">{orderStatus(status).label}</span>
              <span aria-hidden="true" className="h-2 overflow-hidden rounded-full bg-muted">
                <span
                  className={cn("block h-full rounded-full", waitsOnAtelier(status) ? "bg-primary" : "bg-foreground/30")}
                  style={{ width: `${(count / most) * 100}%` }}
                />
              </span>
              <span className="text-right tabular-nums">{count}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
