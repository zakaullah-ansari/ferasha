import { ArrowUpRight, CheckCircle2, ChevronRight } from "lucide-react";
import Link from "next/link";

import type { AttentionItem } from "@/lib/dashboard";

const ROW = "group flex items-center gap-4 py-3 text-sm hover:text-primary";

function Row({ item }: { item: AttentionItem }) {
  const Icon = item.external ? ArrowUpRight : ChevronRight;
  const body = (
    <>
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 font-medium text-primary tabular-nums">
        {item.count}
      </span>
      <span className="flex-1">{item.label}</span>
      <Icon aria-hidden="true" className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </>
  );
  return item.external ? (
    <a href={item.href} target="_blank" rel="noreferrer" className={ROW}>
      {body}
      <span className="sr-only">(opens the admin in a new tab)</span>
    </a>
  ) : (
    <Link href={item.href} className={ROW}>
      {body}
    </Link>
  );
}

/** What is waiting on the owner, each a link to where it is done. */
export function NeedsYou({ items }: { items: readonly AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <CheckCircle2 aria-hidden="true" className="size-8 text-primary" />
        <p className="font-display text-xl">All caught up</p>
        <p className="text-sm text-muted-foreground">Nothing is waiting on the atelier.</p>
      </div>
    );
  }
  return (
    <ul className="divide-y">
      {items.map((item) => (
        <li key={item.id}>
          <Row item={item} />
        </li>
      ))}
    </ul>
  );
}
