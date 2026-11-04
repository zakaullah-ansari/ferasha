/** A dashboard page's title, in the storefront's editorial voice. */
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  /** Actions on the right, e.g. a link into the admin. */
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">{eyebrow}</p>}
        <h1 className="mt-2 font-display text-4xl leading-tight">{title}</h1>
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  );
}
