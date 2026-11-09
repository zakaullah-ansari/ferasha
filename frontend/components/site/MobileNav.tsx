"use client";

import { Menu } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ATELIER } from "@/lib/brand";
import { FULLY_COVERED, OCCASIONS, PRIMARY_NAV } from "@/lib/navigation";

/** Phone menu: categories, occasions and the atelier, in a left-hand sheet. */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={<Button variant="ghost" size="icon" aria-label="Open menu" className="md:hidden" />}>
        <Menu />
      </SheetTrigger>
      <SheetContent side="left" className="w-full sm:max-w-sm">
        <SheetHeader>
          <SheetTitle className="font-display text-2xl">Ferasha</SheetTitle>
        </SheetHeader>
        <nav aria-label="Menu" className="flex flex-1 flex-col gap-8 overflow-y-auto px-4 pb-8">
          <ul className="space-y-4">
            {PRIMARY_NAV.map((link) => (
              <li key={link.href}>
                <Link href={link.href} onClick={close} className="font-display text-2xl">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="space-y-3">
            <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">Shop by occasion</p>
            <ul className="space-y-2">
              {OCCASIONS.map((occasion) => (
                <li key={occasion.href}>
                  <Link href={occasion.href} onClick={close} className="text-sm">
                    {occasion.label}
                  </Link>
                </li>
              ))}
              <li>
                <Link href={FULLY_COVERED.href} onClick={close} className="text-sm text-primary">
                  {FULLY_COVERED.label}
                </Link>
              </li>
            </ul>
          </div>
          <Link href="/account" onClick={close} className="text-sm">
            Your account
          </Link>
          <div className="mt-auto space-y-1 border-t pt-6 text-sm text-muted-foreground">
            <p>Tailored by {ATELIER.name}</p>
            <a href={ATELIER.phoneHref} className="text-foreground underline underline-offset-4">
              {ATELIER.phoneDisplay}
            </a>
          </div>
        </nav>
      </SheetContent>
    </Sheet>
  );
}
