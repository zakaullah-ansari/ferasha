"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api/client";
import type { OrderDetail } from "@/lib/api/types";
import { NEEDS_REASON, orderMoves, orderStatus } from "@/lib/order-status";

/**
 * Moving an order on. Every move is confirmed in a dialog, because each one
 * is recorded on the order's timeline and some are seen by the customer; the
 * ones that undo work or end the order ask for a reason. The API's state
 * machine has the last word: a move it refuses is explained, not hidden.
 */
export function OrderActions({ order }: { order: Pick<OrderDetail, "order_number" | "status" | "next_statuses" | "lines"> }) {
  const router = useRouter();
  const noteId = useId();
  const [move, setMove] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const { suggested, others, canCancel } = orderMoves(order);

  if (!suggested && others.length === 0 && !canCancel) {
    return <p className="text-sm text-muted-foreground">This order is finished; there is nothing left to move.</p>;
  }

  const open = (target: string) => {
    setMove(target);
    setNote("");
    setError(null);
  };
  const needsReason = move !== null && NEEDS_REASON.has(move);

  function confirm() {
    if (!move || (needsReason && !note.trim())) return;
    startTransition(async () => {
      try {
        await api.orders.transition(order.order_number, move, note.trim());
        setMove(null);
        router.refresh();
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "The order could not be moved. Please try again.");
      }
    });
  }

  return (
    <>
      <div className="flex flex-col gap-2">
        {suggested && (
          <Button size="lg" onClick={() => open(suggested)}>
            {orderStatus(suggested).action}
          </Button>
        )}
        {others.map((target) => (
          <Button key={target} variant="outline" onClick={() => open(target)}>
            {orderStatus(target).action}
          </Button>
        ))}
        {canCancel && (
          <Button variant="destructive" className="mt-2" onClick={() => open("cancelled")}>
            {orderStatus("cancelled").action}
          </Button>
        )}
      </div>

      <Dialog open={move !== null} onOpenChange={(next) => !next && !isPending && setMove(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{move && `${orderStatus(move).action}?`}</DialogTitle>
            <DialogDescription>
              {move === "cancelled"
                ? `Order ${order.order_number} will be cancelled and its stock returned. This cannot be undone.`
                : `Order ${order.order_number} moves to “${move ? orderStatus(move).label : ""}”. The change is recorded on its timeline.`}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-2">
            <Label htmlFor={noteId}>{needsReason ? "Reason (required)" : "Note for the timeline (optional)"}</Label>
            <Textarea
              id={noteId}
              value={note}
              maxLength={300}
              onChange={(event) => setNote(event.target.value)}
              required={needsReason}
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <DialogFooter>
            <DialogClose render={<Button variant="outline" disabled={isPending} />}>Keep as it is</DialogClose>
            <Button
              variant={move === "cancelled" ? "destructive" : "default"}
              disabled={isPending || (needsReason && !note.trim())}
              onClick={confirm}
            >
              {isPending ? "Saving…" : move ? orderStatus(move).action : ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
