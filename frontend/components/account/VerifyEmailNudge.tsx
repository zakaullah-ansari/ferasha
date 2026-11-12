"use client";

import { MailCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";

/**
 * Shown in My account until the email is confirmed: why it matters (order
 * and payment emails reach the right inbox) and a one-tap resend. The
 * server limits resends; the button says so instead of failing silently.
 */
export function VerifyEmailNudge({ email }: { readonly email: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "limited">("idle");

  async function resend() {
    setState("sending");
    try {
      await api.session.requestEmailVerification(email);
      setState("sent");
    } catch {
      setState("limited");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-2xl bg-gold-100 px-4 py-3 text-sm text-gold-900 dark:bg-gold-900/40 dark:text-gold-100">
      <MailCheck aria-hidden className="size-5 shrink-0" />
      <p className="min-w-0 flex-1">
        <span className="font-medium">Please confirm your email.</span> We sent a link to {email}, so order and
        delivery updates reach you.
      </p>
      <p role="status" className="sr-only">
        {state === "sent" ? "Link sent." : ""}
      </p>
      {state === "sent" ? (
        <span className="font-medium">Sent. Check your inbox.</span>
      ) : state === "limited" ? (
        <span>Please try again in an hour.</span>
      ) : (
        <Button variant="outline" size="sm" onClick={resend} disabled={state === "sending"}>
          {state === "sending" ? "Sending…" : "Send a new link"}
        </Button>
      )}
    </div>
  );
}
