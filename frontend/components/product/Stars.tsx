import { Star } from "lucide-react";

import { cn } from "@/lib/cn";

/** A rating as five stars, filled to the nearest half. The words are for screen readers; the stars are decoration. */
export function Stars({ rating, className }: { rating: number; className?: string }) {
  const rounded = Math.round(rating * 2) / 2;
  return (
    <span role="img" aria-label={`${rounded} out of 5 stars`} className={cn("inline-flex gap-0.5 text-gold-500", className)}>
      {[1, 2, 3, 4, 5].map((step) => (
        <span key={step} className="relative size-4">
          <Star aria-hidden="true" className="absolute inset-0 size-4 text-border" />
          {rounded >= step - 0.5 && (
            <span className={cn("absolute inset-0 overflow-hidden", rounded < step && "w-1/2")}>
              <Star aria-hidden="true" className="size-4 fill-current" />
            </span>
          )}
        </span>
      ))}
    </span>
  );
}
