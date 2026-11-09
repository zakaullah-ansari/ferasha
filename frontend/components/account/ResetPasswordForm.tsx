"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button, buttonVariants } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";

import { AuthCard } from "./AuthCard";

const EMPTY = { new_password: "", new_password_confirm: "" };

/** From the reset email's link. Success signs out every session and goes to sign-in. */
export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [expired, setExpired] = useState(!token);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const field = (name: keyof typeof EMPTY) => ({
    value: form[name],
    error: errors[name],
    onChange: (event: { target: { value: string } }) => setForm((current) => ({ ...current, [name]: event.target.value })),
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setError(null);
    try {
      await api.session.resetPassword({ token, ...form });
      router.replace("/account/sign-in?next=/account&reason=password-reset");
    } catch (caught) {
      const body = caught instanceof ApiError && caught.status === 400 ? fieldErrors(caught.body) : {};
      if (body.token) setExpired(true);
      else if (Object.keys(body).length > 0) setErrors(body);
      else setError("Your password could not be reset just now. Please try again.");
      setBusy(false);
    }
  }

  if (expired) {
    return (
      <AuthCard title="This link has expired" description="Reset links work once, for one hour. Ask for a new one and use it straight away.">
        <Link href="/account/forgot-password" className={buttonVariants({ size: "lg" })}>
          Send a new link
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password" description="You will be signed out everywhere and asked to sign in with it.">
      <form onSubmit={submit} className="grid gap-4">
        <FormField
          id="reset-new"
          label="New password (at least 10 characters)"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          {...field("new_password")}
        />
        <FormField
          id="reset-confirm"
          label="Confirm the new password"
          type="password"
          autoComplete="new-password"
          required
          {...field("new_password_confirm")}
        />
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? "Saving…" : "Set new password"}
        </Button>
      </form>
    </AuthCard>
  );
}
