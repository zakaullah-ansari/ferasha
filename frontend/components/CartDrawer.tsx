"use client";

import { Minus, Plus, Trash2 } from "lucide-react";
import Link from "next/link";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { formatINR } from "@/lib/format";
import { selectItemCount, useCartStore } from "@/store/useCartStore";

/** The bag. A shadcn Sheet: focus trap, Escape and scroll lock come with it. */
export function CartDrawer() {
  const items = useCartStore((state) => state.items);
  const isOpen = useCartStore((state) => state.isOpen);
  const setDrawerOpen = useCartStore((state) => state.setDrawerOpen);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const removeItem = useCartStore((state) => state.removeItem);
  const count = useCartStore(selectItemCount);
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <Sheet open={isOpen} onOpenChange={setDrawerOpen}>
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="font-display text-xl">Your bag</SheetTitle>
          <SheetDescription>
            {count === 0 ? "Nothing here yet." : `${count} ${count === 1 ? "piece" : "pieces"}`}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4">
          {items.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <p className="text-muted-foreground">Your bag is empty.</p>
              <Link
                href="/products"
                onClick={() => setDrawerOpen(false)}
                className={buttonVariants({ variant: "outline" })}
              >
                Browse the collection
              </Link>
            </div>
          ) : (
            <ul className="divide-y">
              {items.map((item) => (
                <li key={item.variantId} className="flex gap-4 py-4">
                  <div className="size-20 shrink-0 overflow-hidden rounded-lg bg-muted">
                    {item.image && (
                      // Media is served by the API's own image pipeline.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={item.image} alt="" className="size-full object-cover" />
                    )}
                  </div>
                  <div className="flex flex-1 flex-col justify-between">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium leading-snug">{item.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {item.colour} · {item.size}
                        </p>
                      </div>
                      <p className="tabular-nums">{formatINR(item.price * item.quantity)}</p>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <div className="flex items-center rounded-full border">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Decrease quantity of ${item.name}`}
                          disabled={item.quantity <= 1}
                          onClick={() => updateQuantity(item.variantId, item.quantity - 1)}
                        >
                          <Minus />
                        </Button>
                        <span className="w-8 text-center text-xs tabular-nums" aria-live="polite">
                          {item.quantity}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Increase quantity of ${item.name}`}
                          onClick={() => updateQuantity(item.variantId, item.quantity + 1)}
                        >
                          <Plus />
                        </Button>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Remove ${item.name} from bag`}
                        onClick={() => removeItem(item.variantId)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {items.length > 0 && (
          <SheetFooter className="border-t">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-muted-foreground">Subtotal</span>
              <span className="font-display text-xl tabular-nums">{formatINR(subtotal)}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Delivery and GST are calculated at checkout.
            </p>
            <Link
              href="/checkout"
              onClick={() => setDrawerOpen(false)}
              className={buttonVariants({ size: "lg", className: "w-full" })}
            >
              Proceed to checkout
            </Link>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}
