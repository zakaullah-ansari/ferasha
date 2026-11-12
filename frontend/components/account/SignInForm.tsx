"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useValidatedForm } from "@/hooks/use-validated-form";
import { ApiError, api } from "@/lib/api/client";
import type { SocialProvider } from "@/lib/api/types";
import { signInSchema } from "@/lib/auth-validation";

import { AuthCard, type AuthNotice } from "./AuthCard";
import { EmailField } from "./EmailField";
import { SocialSignIn } from "./SocialSignIn";

const IDS = { email: "sign-in-email", password: "sign-in-password" } as const;

export function SignInForm({
  next,
  notice,
  providers = [],
}: {
  readonly next: string;
  readonly notice?: AuthNotice;
  readonly providers?: readonly SocialProvider[];
}) {
  const router = useRouter();
  const form = useValidatedForm(signInSchema, { email: "", password: "" });
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const invalid = form.validateAll();
    if (invalid) {
      document.getElementById(IDS[invalid as keyof typeof IDS])?.focus();
      return;
    }
    setBusy(true);
    try {
      await api.session.signIn({ email: form.values.email.trim(), password: form.values.password, remember });
      router.replace(next);
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status < 500
          ? caught.message
          : "We couldn't sign you in just now. Please try again.",
      );
      setBusy(false);
    }
  }

  const registerHref = `/account/register${next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <AuthCard
      title="Welcome back"
      description="Sign in to check out and follow your orders."
      notice={notice}
      footer={
        <>
          New to Ferasha?&nbsp;
          <Link href={registerHref} className="font-medium text-foreground underline underline-offset-4 hover:text-primary">
            Create an account
          </Link>
        </>
      }
    >
      <div className="grid gap-5">
        <SocialSignIn providers={providers} next={next} />
        <form onSubmit={submit} noValidate className="grid gap-4">
          <EmailField
            id={IDS.email}
            value={form.values.email}
            error={form.errors.email}
            onValue={(value) => form.set("email", value)}
            onBlur={() => form.touch("email")}
          />
          <FormField
            id={IDS.password}
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={form.values.password}
            error={form.errors.password}
            onChange={(event) => form.set("password", event.target.value)}
            onBlur={() => form.touch("password")}
            labelAction={
              <Link
                href="/account/forgot-password"
                className="text-xs font-medium text-primary underline-offset-4 hover:underline"
              >
                Forgot password?
              </Link>
            }
          />
          <div className="flex items-center gap-3">
            <Checkbox
              id="sign-in-remember"
              checked={remember}
              onCheckedChange={(checked) => setRemember(checked === true)}
            />
            <Label htmlFor="sign-in-remember" className="font-normal text-muted-foreground">
              Keep me signed in on this device
            </Label>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </AuthCard>
  );
}
