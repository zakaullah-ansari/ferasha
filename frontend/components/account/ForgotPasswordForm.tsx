"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";

import { AuthCard } from "./AuthCard";

/**
 * The answer is the same whether or not the address has an account, so this
 * page cannot be used to find out who shops here.
 */
export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("sending");
    setError(null);
    try {
      await api.session.requestPasswordReset(email.trim());
      setState("sent");
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 429
          ? "Too many requests. Please wait a few minutes and try again."
          : "We could not send the link just now. Please try again.",
      );
      setState("idle");
    }
  }

  const back = (
    <Link href="/account/sign-in" className="text-foreground underline underline-offset-4">
      Back to sign in
    </Link>
  );

  if (state === "sent") {
    return (
      <AuthCard
        title="Check your email"
        description={`If ${email.trim()} has a Ferasha account, a link to choose a new password is on its way. It works once, for one hour.`}
        footer={back}
      >
        <p className="text-sm text-muted-foreground">Nothing after a few minutes? Check your spam folder, or try again.</p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Forgot your password?" description="Enter your email and we will send you a link to choose a new one." footer={back}>
      <form onSubmit={submit} className="grid gap-4">
        <FormField
          id="forgot-email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" disabled={state === "sending"}>
          {state === "sending" ? "Sending…" : "Send the link"}
        </Button>
      </form>
    </AuthCard>
  );
}
