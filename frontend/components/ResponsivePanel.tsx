"use client";

import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useIsMobile } from "@/hooks/use-mobile";

interface ResponsivePanelProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly title: string;
  readonly description?: React.ReactNode;
  readonly footer?: React.ReactNode;
  readonly children: React.ReactNode;
}

/**
 * One panel, the right shape for the device: on a phone a drawer that rises
 * from the bottom, within thumb reach, and swipes down to close; from tablet
 * width up a sheet from the side. Same header, body and footer either way.
 *
 * No partial-height snap points: the footer (checkout, "Show 9 garments")
 * must always be on screen, and a peek height would push it below the fold.
 *
 * Before hydration (and on the server) it is the sheet, closed: the switch
 * happens before anyone can open it, so nothing flickers.
 */
export function ResponsivePanel({ open, onOpenChange, title, description, footer, children }: ResponsivePanelProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle className="font-display text-2xl">{title}</DrawerTitle>
            {description && <DrawerDescription>{description}</DrawerDescription>}
          </DrawerHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-4">{children}</div>
          {footer && <DrawerFooter className="border-t">{footer}</DrawerFooter>}
        </DrawerContent>
      </Drawer>
    );
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="font-display text-2xl">{title}</SheetTitle>
          {description && <SheetDescription>{description}</SheetDescription>}
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-4">{children}</div>
        {footer && <SheetFooter className="border-t">{footer}</SheetFooter>}
      </SheetContent>
    </Sheet>
  );
}
