import { CircleAlert } from "lucide-react";
import Link from "next/link";

import { POLICIES, type PolicySection } from "@/lib/policies";

/**
 * Shown until the atelier has confirmed every point: a draft must never pass
 * for the shop's final word on returns or privacy.
 */
export function DraftNotice({ points }: { points: readonly string[] }) {
  if (points.length === 0) return null;
  return (
    <aside className="rounded-2xl border border-gold-300 bg-gold-50 p-5 text-sm text-ink-900" aria-label="Draft notice">
      <p className="flex items-center gap-2 font-medium">
        <CircleAlert aria-hidden="true" className="size-4" />
        Draft: awaiting confirmation from the atelier
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5">
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </aside>
  );
}

/** Every help page in one place, so each page links to the others. */
export function HelpNav({ current }: { current: string }) {
  const links = [{ href: "/contact", label: "Contact" }, ...POLICIES.map((p) => ({ href: `/policies/${p.slug}`, label: p.title }))];
  return (
    <nav aria-label="Help" className="text-sm">
      <ul className="flex flex-wrap gap-x-5 gap-y-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              aria-current={link.href === current ? "page" : undefined}
              className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline aria-[current=page]:text-foreground aria-[current=page]:underline"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** The frame every help page shares: navigation, heading, draft notice, body. */
export function HelpPage({
  path,
  eyebrow,
  title,
  summary,
  toConfirm,
  children,
}: {
  path: string;
  eyebrow: string;
  title: string;
  summary: string;
  toConfirm: readonly string[];
  children: React.ReactNode;
}) {
  return (
    <article className="mx-auto max-w-3xl px-5 pt-10 pb-24">
      <HelpNav current={path} />
      <header className="mt-10">
        <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">{eyebrow}</p>
        <h1 className="mt-3 font-display text-display-sm leading-tight">{title}</h1>
        <p className="mt-3 text-muted-foreground">{summary}</p>
      </header>
      <div className="mt-8">
        <DraftNotice points={toConfirm} />
      </div>
      <div className="mt-10 space-y-10">{children}</div>
    </article>
  );
}

export function PolicySections({ sections }: { sections: readonly PolicySection[] }) {
  return sections.map((section) => (
    <section key={section.heading}>
      <h2 className="font-display text-2xl">{section.heading}</h2>
      {section.paragraphs?.map((paragraph) => (
        <p key={paragraph} className="mt-3 leading-relaxed text-muted-foreground">
          {paragraph}
        </p>
      ))}
      {section.items && (
        <ul className="mt-3 list-disc space-y-2 pl-5 leading-relaxed text-muted-foreground">
          {section.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  ));
}
