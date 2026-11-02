"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CheckoutStepper } from "@/components/CheckoutStepper";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";
import { useBagHydrated, useCartStore } from "@/store/useCartStore";

type Stage =
  | { readonly kind: "syncing" }
  | { readonly kind: "empty" }
  | { readonly kind: "ready"; readonly removed: readonly string[] }
  | { readonly kind: "failed"; readonly message: string };

/**
 * Hands the browser bag to the server, then runs the stepper.
 *
 * The bag lives in localStorage so guests can shop; the server cart is what
 * checkout prices. Replacing (not merging) it here means the order is exactly
 * what the customer saw in the bag - never a leftover from another session.
 */
export function CheckoutFlow() {
  const router = useRouter();
  const hydrated = useBagHydrated();
  const items = useCartStore((state) => state.items);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);
  const [stage, setStage] = useState<Stage>({ kind: "syncing" });

  useEffect(() => {
    if (!hydrated) return;
    // Read once at entry; edits from here on happen in the review step.
    const bag = useCartStore.getState().items;
    if (bag.length === 0) {
      setStage({ kind: "empty" });
      return;
    }
    let cancelled = false;
    api.cart
      .replace(bag.map((item) => ({ variant_id: item.variantId, quantity: item.quantity })))
      .then(({ skipped }) => {
        if (cancelled) return;
        const removed = bag.filter((item) => skipped.includes(item.variantId));
        removed.forEach((item) => removeItem(item.variantId));
        setStage(
          removed.length === bag.length
            ? { kind: "empty" }
            : { kind: "ready", removed: removed.map((item) => item.name) },
        );
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/account/sign-in?next=/checkout");
          return;
        }
        setStage({ kind: "failed", message: "We couldn't load your bag. Please refresh to try again." });
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, removeItem, router]);

  if (stage.kind === "syncing") {
    return (
      <p role="status" className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        Preparing your order…
      </p>
    );
  }

  if (stage.kind === "empty" || (stage.kind === "ready" && items.length === 0)) {
    return (
      <div className="space-y-4 text-center">
        <p className="text-muted-foreground">Your bag is empty.</p>
        <Link href="/products" className={buttonVariants({ variant: "outline" })}>
          Browse the collection
        </Link>
      </div>
    );
  }

  if (stage.kind === "failed") {
    return (
      <p role="alert" className="text-destructive">
        {stage.message}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {stage.removed.length > 0 && (
        <p role="status" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
          {stage.removed.join(", ")} {stage.removed.length === 1 ? "is" : "are"} no longer
          available and {stage.removed.length === 1 ? "was" : "were"} removed from your bag.
        </p>
      )}
      <CheckoutStepper
        onPlaced={(order) => {
          clearCart();
          router.push(`/orders/${encodeURIComponent(order.order_number)}?placed=1`);
        }}
      />
    </div>
  );
}
