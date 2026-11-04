/** Page numbers for any paginated list (the collection, the dashboard's orders). */

export type PageItem = number | "gap";

/**
 * Page numbers to show: always the first and last, the current one and its
 * neighbours, with a gap where pages are skipped. A gap never stands in for a
 * single page - that page is shown instead.
 */
export function pageWindow(current: number, total: number): PageItem[] {
  const shown = [...new Set([1, current - 1, current, current + 1, total])]
    .filter((page) => page >= 1 && page <= total)
    .sort((a, b) => a - b);
  const items: PageItem[] = [];
  for (const page of shown) {
    const previous = items.at(-1);
    if (typeof previous === "number" && page - previous === 2) items.push(previous + 1);
    else if (typeof previous === "number" && page - previous > 2) items.push("gap");
    items.push(page);
  }
  return items;
}
