import { Badge } from "@/components/ui/badge";
import { waitsOnAtelier } from "@/lib/dashboard";
import { orderStatus } from "@/lib/order-status";

const ENDED = new Set(["cancelled", "refunded", "returned"]);

/** Filled when the order waits on the atelier, so the owner's next jobs stand out in any list. */
export function OrderStatusBadge({ status }: { status: string }) {
  const variant = waitsOnAtelier(status) ? "default" : ENDED.has(status) ? "outline" : "secondary";
  return <Badge variant={variant}>{orderStatus(status).label}</Badge>;
}
