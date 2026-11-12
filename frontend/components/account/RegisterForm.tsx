"use client";

import { Check, Circle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useValidatedForm } from "@/hooks/use-validated-form";
import { ApiError, api } from "@/lib/api/client";
import type { SocialProvider } from "@/lib/api/types";
import { PASSWORD_MIN, passwordRules, registerSchema } from "@/lib/auth-validation";
import { cn } from "@/lib/cn";

import { AuthCard } from "./AuthCard";
import { EmailField } from "./EmailField";
import { SocialSignIn } from "./SocialSignIn";
import { TermsLinks } from "./TermsLinks";

const IDS = {
  full_name: "register-name",
  email: "register-email",
  password: "register-password",
  accept_terms: "register-terms",
} as const;

/** The password rules as a live checklist; ticks turn green as each is met. */
function PasswordChecklist({ password }: { readonly password: string }) {
  return (
    <span className="flex flex-wrap gap-x-4 gap-y-1">
      {passwordRules(password).map((rule) => {
        const Icon = rule.met ? Check : Circle;
        return (
          <span key={rule.id} className={cn("inline-flex items-center gap-1", rule.met && "text-primary")}>
            <Icon aria-hidden className={rule.met ? "size-3.5" : "size-2.5"} />
            {rule.label}
            <span className="sr-only">{rule.met ? " (done)" : ""}</span>
          </span>
        );
      })}
    </span>
  );
}

/**
 * Four things and one tick: name, email, password (shown on request, so no
 * "confirm" box), terms. Mobile is asked for at checkout and editable in
 * My account, so it no longer slows the first step down.
 */
export function RegisterForm({
  next,
  providers = [],
}: {
  readonly next: string;
  readonly providers?: readonly SocialProvider[];
}) {
  const router = useRouter();
  const form = useValidatedForm(registerSchema, { full_name: "", email: "", password: "", accept_terms: false });
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
    const { full_name, email, password } = form.values;
    try {
      await api.session.register({ full_name: full_name.trim(), email: email.trim(), password, accept_terms: true });
      router.replace(next);
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        const serverErrors = fieldErrors(caught.body);
        form.setErrors(serverErrors);
        const first = (Object.keys(IDS) as (keyof typeof IDS)[]).find((name) => name in serverErrors);
        if (first) document.getElementById(IDS[first])?.focus();
        else setError("Please check the highlighted fields.");
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
    <AuthCard
      title="Create your account"
      description="Follow your orders, from the atelier to your door, in one place."
      footer={
        <>
          Already have an account?&nbsp;
          <Link href={signInHref} className="font-medium text-foreground underline underline-offset-4 hover:text-primary">
            Sign in
          </Link>
        </>
      }
    >
      <div className="grid gap-5">
        <SocialSignIn providers={providers} next={next} />
        <form onSubmit={submit} noValidate className="grid gap-4">
          <FormField
            id={IDS.full_name}
            label="Full name"
            autoComplete="name"
            placeholder="Ayesha Khan"
            required
            maxLength={180}
            value={form.values.full_name}
            error={form.errors.full_name}
            onChange={(event) => form.set("full_name", event.target.value)}
            onBlur={() => form.touch("full_name")}
          />
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
            autoComplete="new-password"
            placeholder={`${PASSWORD_MIN}+ characters`}
            required
            minLength={PASSWORD_MIN}
            value={form.values.password}
            error={form.errors.password}
            onChange={(event) => form.set("password", event.target.value)}
            onBlur={() => form.touch("password")}
            description={<PasswordChecklist password={form.values.password} />}
          />
          <div className="grid gap-2">
            <div className="flex items-start gap-3">
              <Checkbox
                id={IDS.accept_terms}
                checked={form.values.accept_terms}
                onCheckedChange={(checked) => form.set("accept_terms", checked === true)}
                aria-invalid={form.errors.accept_terms ? true : undefined}
                aria-describedby={form.errors.accept_terms ? "register-terms-error" : undefined}
              />
              <Label htmlFor={IDS.accept_terms} className="block font-normal leading-snug text-muted-foreground">
                I accept <TermsLinks />.
              </Label>
            </div>
            {form.errors.accept_terms && (
              <p id="register-terms-error" className="text-sm text-destructive">
                {form.errors.accept_terms}
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
      </div>
    </AuthCard>
  );
}
