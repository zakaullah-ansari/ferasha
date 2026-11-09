"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api/client";

import { AuthCard } from "./AuthCard";

/**
 * A button, not an automatic confirm on load: mail scanners open links before
 * people do, and must not spend the token. The request goes through the API
 * proxy, so it is rate limited per visitor.
 */
export function VerifyEmail({ token }: { token: string }) {
  const [state, setState] = useState<"ready" | "busy" | "done" | "failed">(token ? "ready" : "failed");

  async function confirm() {
    setState("busy");
    try {
      await api.session.confirmEmail(token);
      setState("done");
    } catch {
      setState("failed");
    }
  }

  if (state === "done") {
    return (
      <AuthCard title="Email confirmed" description="Thank you. Order confirmations and atelier updates will reach you here.">
        <Link href="/products" className={buttonVariants({ size: "lg" })}>
          Explore the collection
        </Link>
      </AuthCard>
    );
  }
  if (state === "failed") {
    return (
      <AuthCard title="This link has expired" description="Confirmation links work once, for 48 hours. Sign in to your account and we can send a new one.">
        <Link href="/account" className={buttonVariants({ size: "lg" })}>
          Go to your account
        </Link>
      </AuthCard>
    );
  }
  return (
    <AuthCard title="Confirm your email" description="One step so we can send you order confirmations and updates.">
      <Button size="lg" className="w-full" disabled={state === "busy"} onClick={confirm}>
        {state === "busy" ? "Confirming…" : "Confirm my email"}
      </Button>
    </AuthCard>
  );
}
