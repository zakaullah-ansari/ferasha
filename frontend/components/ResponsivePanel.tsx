"use client";

import { XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
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
 * One panel, one design, the right direction for the device: the theme's
 * rounded, floating drawer. On a phone it rises from the bottom, within
 * thumb reach, and swipes down to close; from tablet width up it slides in
 * from the right and swipes right to close. A close button is always there
 * for mouse and keyboard; Escape and the backdrop close it too.
 *
 * No partial-height snap points: the footer (checkout, "Show 9 garments")
 * must always be on screen, and a peek height would push it below the fold.
 *
 * Before hydration (and on the server) it is the side drawer, closed: the
 * direction is settled before anyone can open it, so nothing flickers.
 */
export function ResponsivePanel({ open, onOpenChange, title, description, footer, children }: ResponsivePanelProps) {
  const isMobile = useIsMobile();

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      swipeDirection={isMobile ? "down" : "right"}
      showSwipeHandle={isMobile}
    >
      {/* A little wider than the drawer's 24rem default: bag lines carry a photo, name and price. */}
      <DrawerContent className="data-[swipe-axis=x]:sm:[--drawer-content-width:28rem]">
        <DrawerHeader className="relative pr-14 group-data-[swipe-axis=y]/drawer-popup:px-14">
          <DrawerTitle className="font-display text-2xl">{title}</DrawerTitle>
          {description && <DrawerDescription>{description}</DrawerDescription>}
          <DrawerClose render={<Button variant="ghost" size="icon-sm" className="absolute top-3 right-3" />}>
            <XIcon />
            <span className="sr-only">Close</span>
          </DrawerClose>
        </DrawerHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-4">{children}</div>
        {footer && <DrawerFooter className="border-t pt-4">{footer}</DrawerFooter>}
      </DrawerContent>
    </Drawer>
  );
}
