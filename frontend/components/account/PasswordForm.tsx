"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";

const EMPTY = { current_password: "", new_password: "", new_password_confirm: "" };

/**
 * Changing the password signs out every session, this one included (a stolen
 * session must not survive it), so success goes straight to sign-in.
 */
export function PasswordForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
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
      await api.session.changePassword(form);
      // The server has already revoked the session; clear its cookies too.
      await api.session.signOut().catch(() => undefined);
      router.replace("/account/sign-in?next=/account&reason=password-changed");
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        setErrors(fieldErrors(caught.body));
        setError("Please check the highlighted fields.");
      } else {
        setError("Your password could not be changed just now. Please try again.");
      }
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <FormField
        id="password-current"
        label="Current password"
        type="password"
        autoComplete="current-password"
        required
        {...field("current_password")}
      />
      <FormField
        id="password-new"
        label="New password (at least 10 characters)"
        type="password"
        autoComplete="new-password"
        required
        minLength={10}
        {...field("new_password")}
      />
      <FormField
        id="password-confirm"
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
      <p className="text-xs text-muted-foreground">You will be signed out everywhere and asked to sign in again.</p>
      <Button type="submit" variant="outline" disabled={busy} className="justify-self-start">
        {busy ? "Changing…" : "Change password"}
      </Button>
    </form>
  );
}
