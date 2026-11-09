/**
 * The owner dashboard's reading of the summary API: what changed, and what is
 * waiting on the owner. Pure, so the wording and the thresholds are tested
 * without rendering anything.
 */

import { ADMIN_LINKS } from "@/lib/admin-links";
import type { DashboardSummary } from "@/lib/api/types";

export interface Change {
  /** Whole percent, always positive; the direction says which way. */
  readonly percent: number;
  readonly direction: "up" | "down" | "flat";
}

/** Against nothing there is no percentage to give, so none is invented. */
export function change(current: number, previous: number): Change | null {
  if (previous <= 0) return null;
  const percent = Math.round((Math.abs(current - previous) / previous) * 100);
  return { percent, direction: percent === 0 ? "flat" : current > previous ? "up" : "down" };
}

export interface AttentionItem {
  readonly id: string;
  readonly count: number;
  readonly label: string;
  readonly href: string;
  /** Opens the Django admin, in a new tab. */
  readonly external?: boolean;
}

/** Open stages that wait on the atelier, and where to deal with each. */
const STAGE_TASKS: Readonly<Record<string, { label: string; view: string }>> = {
  payment_confirmed: { label: "Paid, ready to start", view: "to-start" },
  measurement_review: { label: "Measurements to review", view: "atelier" },
  quality_check: { label: "Waiting for quality check", view: "atelier" },
  packed: { label: "Packed, ready to ship", view: "to-ship" },
  return_requested: { label: "Returns to handle", view: "returns" },
};

/** True for a stage where the order waits on the atelier rather than on the customer or the courier. */
export function waitsOnAtelier(status: string): boolean {
  return status in STAGE_TASKS;
}

/** Everything waiting on the owner, in the order the work happens. Empty means all caught up. */
export function attentionItems(summary: DashboardSummary): AttentionItem[] {
  const items: AttentionItem[] = summary.pipeline.flatMap(({ status, count }) => {
    const task = STAGE_TASKS[status];
    return task && count > 0
      ? [{ id: status, count, label: task.label, href: `/dashboard/orders?view=${task.view}` }]
      : [];
  });
  const { reviews_pending, photos_needing_review } = summary.moderation;
  if (reviews_pending > 0) {
    items.push({ id: "reviews", count: reviews_pending, label: "Reviews to moderate", href: ADMIN_LINKS.pendingReviews, external: true });
  }
  if (photos_needing_review > 0) {
    items.push({
      id: "photos",
      count: photos_needing_review,
      label: "Photos needing a privacy check",
      href: ADMIN_LINKS.photosToReview,
      external: true,
    });
  }
  if (summary.low_stock.length > 0) {
    items.push({ id: "stock", count: summary.low_stock.length, label: "Sizes running low", href: "#low-stock" });
  }
  return items;
}

/** The orders list's URL: a view (tab), an optional search, a page. Defaults are left out. */
export function ordersHref({ view, q, page = 1 }: { view: string; q?: string; page?: number }): string {
  const params = new URLSearchParams({ view });
  if (q) params.set("q", q);
  if (page > 1) params.set("page", String(page));
  return `/dashboard/orders?${params}`;
}
