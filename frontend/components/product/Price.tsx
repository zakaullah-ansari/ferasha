import { cn } from "@/lib/cn";
import { formatINR } from "@/lib/format";
import { percentOff } from "@/lib/merchandising";

interface PriceProps {
  readonly price: string;
  readonly compareAt: string | null;
  readonly className?: string;
  /** Size of the struck-through price relative to the current one. */
  readonly wasClassName?: string;
}

/**
 * The selling price, and the struck-through price beside it when the garment
 * is genuinely reduced (percentOff decides; bad data shows no sale at all).
 * One component for the card and the product page so they never disagree.
 */
export function Price({ price, compareAt, className, wasClassName = "text-sm" }: PriceProps) {
  const onSale = percentOff(price, compareAt) !== null;

  return (
    <p className={cn("flex flex-wrap items-baseline gap-x-2.5", className)}>
      <span className={cn(onSale && "font-medium text-primary")}>
        {onSale && <span className="sr-only">Now </span>}
        {formatINR(price)}
      </span>
      {onSale && compareAt && (
        <del className={cn("text-muted-foreground", wasClassName)}>
          <span className="sr-only">was </span>
          {formatINR(compareAt)}
        </del>
      )}
    </p>
  );
}
