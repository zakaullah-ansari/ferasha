/**
 * Order statuses, in the order the work happens, with the words each audience
 * sees. Values mirror backend-core orders.OrderStatus; which moves are allowed
 * is decided by the API's state machine (`next_statuses`), never here.
 */

import type { OrderDetail } from "@/lib/api/types";

export interface OrderStatusInfo {
  readonly value: string;
  /** The atelier's word for the stage. */
  readonly label: string;
  /** The customer's, where they differ: a customer is never "in quality check". */
  readonly customer: string;
  /** The button that moves an order into this stage. */
  readonly action: string;
}

export const ORDER_STATUSES: readonly OrderStatusInfo[] = [
  { value: "draft", label: "Draft", customer: "Draft", action: "Return to draft" },
  { value: "placed", label: "Awaiting payment", customer: "Awaiting payment", action: "Mark placed" },
  { value: "payment_confirmed", label: "Paid, to start", customer: "Payment received", action: "Mark payment received" },
  { value: "measurement_review", label: "Measurement review", customer: "Reviewing measurements", action: "Review measurements" },
  { value: "in_atelier", label: "In the atelier", customer: "In the atelier", action: "Start in the atelier" },
  { value: "stitching", label: "Stitching", customer: "Being stitched", action: "Start stitching" },
  { value: "quality_check", label: "Quality check", customer: "Final quality check", action: "Send to quality check" },
  { value: "packed", label: "Packed, to ship", customer: "Packed", action: "Mark packed" },
  { value: "shipped", label: "Shipped", customer: "On its way", action: "Mark shipped" },
  { value: "delivered", label: "Delivered", customer: "Delivered", action: "Mark delivered" },
  { value: "return_requested", label: "Return requested", customer: "Return requested", action: "Record a return request" },
  { value: "returned", label: "Returned", customer: "Returned", action: "Mark returned" },
  { value: "refunded", label: "Refunded", customer: "Refunded", action: "Mark refunded" },
  { value: "cancelled", label: "Cancelled", customer: "Cancelled", action: "Cancel order" },
];

const BY_VALUE = new Map(ORDER_STATUSES.map((status) => [status.value, status]));

/** Falls back to the raw value, so a status added on the API still shows. */
export function orderStatus(value: string): OrderStatusInfo {
  return BY_VALUE.get(value) ?? { value, label: value, customer: value, action: value };
}

/** Moves that need a written reason: they undo work or end the order. */
export const NEEDS_REASON: ReadonlySet<string> = new Set(["cancelled", "measurement_review", "return_requested", "refunded"]);

export interface OrderMoves {
  /** The usual next step, offered as the main button. */
  readonly suggested?: string;
  /** Every other allowed move, in working order. */
  readonly others: readonly string[];
  readonly canCancel: boolean;
}

const position = (value: string) => ORDER_STATUSES.findIndex((status) => status.value === value);

/**
 * How to offer an order's allowed moves. A paid order made to measure goes to
 * the atelier; a ready-made one can go straight to packing. Otherwise the next
 * stage forward is suggested; moves back, and moves that need a reason, never are.
 */
export function orderMoves(order: Pick<OrderDetail, "status" | "next_statuses" | "lines">): OrderMoves {
  const here = position(order.status);
  const moves = order.next_statuses
    .filter((move) => move !== "cancelled")
    .sort((a, b) => position(a) - position(b));
  const forward = moves.filter((move) => position(move) > here && !NEEDS_REASON.has(move));
  const preferred =
    order.status === "payment_confirmed"
      ? order.lines.some((line) => line.is_bespoke) ? "in_atelier" : "packed"
      : undefined;
  const suggested = preferred && forward.includes(preferred) ? preferred : forward[0];
  return {
    suggested,
    others: moves.filter((move) => move !== suggested),
    canCancel: order.next_statuses.includes("cancelled"),
  };
}

export interface OrderView {
  readonly id: string;
  readonly label: string;
  readonly statuses: readonly string[];
}

/** The order list's tabs: stages grouped the way the owner works through them. */
export const ORDER_VIEWS: readonly OrderView[] = [
  { id: "to-start", label: "To start", statuses: ["payment_confirmed"] },
  { id: "atelier", label: "In the atelier", statuses: ["measurement_review", "in_atelier", "stitching", "quality_check"] },
  { id: "to-ship", label: "To ship", statuses: ["packed"] },
  { id: "shipped", label: "Shipped", statuses: ["shipped"] },
  { id: "unpaid", label: "Awaiting payment", statuses: ["placed"] },
  { id: "returns", label: "Returns", statuses: ["return_requested", "returned"] },
  { id: "closed", label: "Closed", statuses: ["delivered", "refunded", "cancelled"] },
  { id: "all", label: "All", statuses: [] },
];

export const DEFAULT_ORDER_VIEW = ORDER_VIEWS[0]!;

export function orderView(id: string | undefined): OrderView {
  return ORDER_VIEWS.find((view) => view.id === id) ?? DEFAULT_ORDER_VIEW;
}
