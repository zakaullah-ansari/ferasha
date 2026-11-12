import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { StripedPattern } from "@/components/ui/striped-pattern";
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
 * verification): one centred card on a silk weave.
 */
export function AuthPage({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate overflow-hidden">
      <SilkWeave />
      <div className="mx-auto flex max-w-6xl justify-center px-4 py-12 sm:px-5 md:py-20">{children}</div>
    </div>
  );
}

/**
 * A fine twill, the way silk looks up close: forest-green threads one way,
 * gold the other, on a mint ground, under a soft diagonal sheen, fading out
 * toward the edges so the frame never ends in a hard line above the footer.
 * Still SVG, a few hundred bytes, nothing animating: free on a phone.
 * Decorative only.
 */
function SilkWeave() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10 bg-accent mask-radial-from-60% mask-radial-to-100% mask-b-from-55%"
    >
      <StripedPattern direction="left" width={6} height={6} className="text-primary/30" />
      <StripedPattern direction="right" width={6} height={6} className="text-gold-500/45" />
      <div className="absolute inset-0 z-10 bg-linear-120 from-transparent via-background/60 to-transparent" />
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
    // Solid, not frosted: a weave seen through glass reads as noise behind the
    // form. The entrance is CSS (tw-animate), so it plays before JavaScript
    // loads and never holds the form back.
    <Card className="w-full max-w-md shadow-xl shadow-primary/10animate-in fade-in-0 slide-in-from-bottom-3 duration-500 ease-out motion-reduce:animate-none sm:[--card-spacing:--spacing(8)]">
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
