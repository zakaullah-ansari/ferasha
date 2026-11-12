import type { ComponentType, SVGProps } from "react";

import { buttonVariants } from "@/components/ui/button";
import { FieldSeparator } from "@/components/ui/field";
import type { SocialProvider } from "@/lib/api/types";
import { oauthStartHref } from "@/lib/oauth";

import { TermsLinks } from "./TermsLinks";

/** Google's "G" mark in its own colours, as Google's sign-in branding rules require. */
function GoogleMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <path fill="#4285F4" d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.46a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.58-5.17 3.58-8.81Z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.9l-3.88-3.01c-1.07.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.71-4.95H1.28v3.11A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.29 14.29A7.2 7.2 0 0 1 4.91 12c0-.8.14-1.57.38-2.29V6.6H1.28a12 12 0 0 0 0 10.8l4.01-3.11Z" />
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.34.61 4.59 1.8l3.44-3.44A11.94 11.94 0 0 0 12 0 12 12 0 0 0 1.28 6.6l4.01 3.11C6.23 6.88 8.88 4.77 12 4.77Z" />
    </svg>
  );
}

/** Marks for providers we know. A new provider without one still gets a text button. */
const MARKS: Readonly<Record<string, ComponentType<SVGProps<SVGSVGElement>>>> = {
  google: GoogleMark,
};

/**
 * "Continue with Google" (and any provider Django switches on later), then
 * an "or" divider before the email form. Renders nothing when no provider
 * is configured, so a half-set-up provider never shows a dead button.
 *
 * Plain links, not buttons: they work before the page hydrates and the whole
 * round trip happens in route handlers.
 */
export function SocialSignIn({
  providers,
  next,
}: {
  readonly providers: readonly SocialProvider[];
  readonly next: string;
}) {
  if (providers.length === 0) return null;
  return (
    <>
      <div className="grid gap-2">
        {providers.map((provider) => {
          const Mark = MARKS[provider.id];
          return (
            <a
              key={provider.id}
              href={oauthStartHref(provider.id, next)}
              className={buttonVariants({ variant: "outline", size: "lg", className: "w-full" })}
            >
              {Mark && <Mark />}
              Continue with {provider.name}
            </a>
          );
        })}
        <p className="text-center text-xs text-muted-foreground">
          By continuing, you accept <TermsLinks />.
        </p>
      </div>
      {/* The separator's label sits on the card, not the page background. */}
      <FieldSeparator className="*:data-[slot=field-separator-content]:bg-card">or with email</FieldSeparator>
    </>
  );
}
