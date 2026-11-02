"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api/client";
import type { Registration } from "@/lib/api/types";

const EMPTY: Registration = {
  full_name: "",
  email: "",
  phone: "",
  password: "",
  password_confirm: "",
  accept_terms: false,
};

type TextField = Exclude<keyof Registration, "accept_terms">;

export function RegisterForm({ next }: { readonly next: string }) {
  const router = useRouter();
  const [form, setForm] = useState<Registration>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const field = (name: TextField) => ({
    value: form[name] ?? "",
    error: errors[name],
    onChange: (event: { target: { value: string } }) =>
      setForm((current) => ({ ...current, [name]: event.target.value })),
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      await api.session.register({ ...form, phone: form.phone || undefined });
      router.replace(next);
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        setErrors(fieldErrors(caught.body));
        setError("Please check the highlighted fields.");
      } else {
        setError(
          caught instanceof ApiError && caught.status < 500
            ? caught.message
            : "We couldn't create your account just now. Please try again.",
        );
      }
      setBusy(false);
    }
  }

  const signInHref = `/account/sign-in${next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="font-display text-2xl">Create your account</CardTitle>
        <CardDescription>Save your addresses and follow your orders in one place.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4">
          <FormField id="register-name" label="Full name" autoComplete="name" required {...field("full_name")} />
          <FormField id="register-email" label="Email" type="email" autoComplete="email" required {...field("email")} />
          <FormField id="register-phone" label="Mobile (optional)" type="tel" autoComplete="tel" {...field("phone")} />
          <FormField
            id="register-password"
            label="Password (at least 10 characters)"
            type="password"
            autoComplete="new-password"
            required
            minLength={10}
            {...field("password")}
          />
          <FormField
            id="register-password-confirm"
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            required
            {...field("password_confirm")}
          />
          <div className="grid gap-2">
            <div className="flex items-start gap-3">
              <Checkbox
                id="register-terms"
                checked={form.accept_terms}
                onCheckedChange={(checked) =>
                  setForm((current) => ({ ...current, accept_terms: checked === true }))
                }
                aria-invalid={errors.accept_terms ? true : undefined}
                aria-describedby={errors.accept_terms ? "register-terms-error" : undefined}
              />
              <Label htmlFor="register-terms" className="font-normal leading-snug">
                I accept the terms of service and privacy policy.
              </Label>
            </div>
            {errors.accept_terms && (
              <p id="register-terms-error" className="text-sm text-destructive">
                {errors.accept_terms}
              </p>
            )}
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={busy}>
            {busy ? "Creating your account…" : "Create account"}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="text-sm text-muted-foreground">
        Already have an account?&nbsp;
        <Link href={signInHref} className="text-foreground underline underline-offset-4">
          Sign in
        </Link>
      </CardFooter>
    </Card>
  );
}
