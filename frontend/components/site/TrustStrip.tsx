import { Ruler, Scissors, ShieldCheck, Truck, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import { TRUST_POINTS, type TrustPointId } from "@/lib/trust";

const ICONS: Readonly<Record<TrustPointId, LucideIcon>> = {
  coverage: ShieldCheck,
  tailored: Scissors,
  bespoke: Ruler,
  delivery: Truck,
};

/**
 * The shop's promises where the decision is made. `compact` is a quiet list
 * beside the buy button; the default is a band of four.
 */
export function TrustStrip({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <ul
      aria-label="Our promises"
      className={cn(compact ? "grid gap-2.5" : "grid gap-6 sm:grid-cols-2 lg:grid-cols-4", className)}
    >
      {TRUST_POINTS.map(({ id, title, detail }) => {
        const Icon = ICONS[id];
        return (
          <li key={id} className="flex items-start gap-3">
            <Icon aria-hidden="true" className={cn("shrink-0 text-primary", compact ? "mt-0.5 size-4" : "size-5")} />
            <span className={compact ? "text-xs leading-relaxed" : "text-sm"}>
              <span className="block font-medium text-foreground">{title}</span>
              <span className="text-muted-foreground">{detail}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
