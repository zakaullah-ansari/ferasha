"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { cn } from "@/lib/cn";
import { isCurrentLink } from "@/lib/nav-active";
import { PRIMARY_NAV } from "@/lib/navigation";

/**
 * The header's category links, after Housiq's: a gold-green underline draws
 * out from the centre on hover or keyboard focus and stays under the section
 * being shown. Without motion it simply appears.
 */
export function PrimaryNavLinks() {
  return (
    // Reading the query needs a Suspense boundary, or every static page would
    // fall back to client rendering; the fallback is the same list, unlit.
    <Suspense fallback={<LinkList />}>
      <CurrentLinkList />
    </Suspense>
  );
}

function CurrentLinkList() {
  const pathname = usePathname();
  const search = useSearchParams();
  return <LinkList isCurrent={(href) => isCurrentLink(href, pathname, search)} />;
}

function LinkList({ isCurrent = () => false }: { isCurrent?: (href: string) => boolean }) {
  return (
    <ul className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
      {PRIMARY_NAV.map((link) => {
        const current = isCurrent(link.href);
        return (
          <li key={link.href}>
            <Link
              href={link.href}
              aria-current={current ? "page" : undefined}
              className="group relative py-1 transition-colors duration-300 hover:text-foreground aria-[current=page]:font-medium aria-[current=page]:text-foreground"
            >
              {link.label}
              <span
                aria-hidden="true"
                className={cn(
                  "absolute inset-x-0 -bottom-0.5 h-0.5 rounded-full bg-primary transition-transform duration-300 ease-luxury motion-reduce:transition-none",
                  current ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100 group-focus-visible:scale-x-100",
                )}
              />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
