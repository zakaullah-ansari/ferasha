import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { TRUST_POINTS } from "@/lib/trust";

export interface AuthNotice {
  /** A fixed message from the app (never text taken from the URL). */
  readonly message: string;
  readonly tone: "info" | "error";
}

/** One quiet line of what the shop already promises (same source as the trust strip). */
const REASSURANCE = TRUST_POINTS.filter((point) => point.id === "coverage" || point.id === "tailored")
  .map((point) => point.title)
  .join(" · ");

/**
 * The page frame every account screen shares (sign-in, register, reset,
 * verification): a soft wash of the brand's gold and green behind one
 * centred card. Decorative layers are aria-hidden and ignore the pointer.
 */
export function AuthPage({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-32 -left-24 size-[28rem] rounded-full bg-gold-200/50 blur-3xl" />
        <div className="absolute -right-24 -bottom-40 size-[32rem] rounded-full bg-primary/15 blur-3xl" />
      </div>
      <div className="mx-auto flex max-w-6xl justify-center px-4 py-10 sm:px-5 md:py-16">{children}</div>
    </div>
  );
}

/** The card itself: centred heading, optional notice, the form, a footer link and the reassurance line. */
export function AuthCard({
  title,
  description,
  notice,
  footer,
  children,
}: {
  title: string;
  description: string;
  notice?: AuthNotice;
  footer?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="w-full max-w-md bg-card/90 shadow-xl shadow-foreground/5 backdrop-blur-sm sm:[--card-spacing:--spacing(8)]">
      <CardHeader className="text-center">
        <CardTitle className="font-display text-3xl">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        {notice && (
          <p
            role={notice.tone === "error" ? "alert" : "status"}
            className={cn(
              "mt-2 rounded-xl px-3 py-2 text-left text-sm",
              notice.tone === "error" ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary",
            )}
          >
            {notice.message}
          </p>
        )}
      </CardHeader>
      <CardContent>{children}</CardContent>
      <CardFooter className="flex-col gap-4 text-center text-sm text-muted-foreground">
        {footer && <div>{footer}</div>}
        <p className="text-xs">{REASSURANCE}</p>
      </CardFooter>
    </Card>
  );
}
