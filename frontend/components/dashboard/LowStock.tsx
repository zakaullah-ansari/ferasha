import { ArrowUpRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ADMIN_LINKS } from "@/lib/admin-links";
import type { DashboardSummary } from "@/lib/api/types";

/** Sizes about to sell out, scarcest first; each opens its variant in the admin to restock. */
export function LowStock({ rows }: { rows: DashboardSummary["low_stock"] }) {
  if (rows.length === 0) {
    return <p className="py-6 text-sm text-muted-foreground">Every size is comfortably in stock.</p>;
  }
  return (
    <Table>
      <TableCaption className="sr-only">Sizes running low</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Garment</TableHead>
          <TableHead>Size</TableHead>
          <TableHead className="text-right">Left</TableHead>
          <TableHead>
            <span className="sr-only">Restock</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.sku}>
            <TableCell className="max-w-48">
              <span className="block truncate">{row.product_name}</span>
              <span className="text-xs text-muted-foreground">{row.colour}</span>
            </TableCell>
            <TableCell>{row.size}</TableCell>
            <TableCell className="text-right tabular-nums">
              {row.stock_quantity === 0 ? <Badge variant="destructive">Sold out</Badge> : row.stock_quantity}
            </TableCell>
            <TableCell>
              <a
                href={ADMIN_LINKS.variant(row.sku)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
              >
                Restock
                <ArrowUpRight aria-hidden="true" className="size-3.5" />
                <span className="sr-only">{` ${row.product_name}, size ${row.size} (opens the admin in a new tab)`}</span>
              </a>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
