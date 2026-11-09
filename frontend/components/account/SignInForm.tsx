"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api/client";

export function SignInForm({ next, notice }: { readonly next: string; readonly notice?: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.session.signIn({ email, password });
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
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="font-display text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to check out and follow your orders.</CardDescription>
        {notice && (
          <p role="status" className="mt-2 rounded-xl bg-primary/10 px-3 py-2 text-sm text-primary">
            {notice}
          </p>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4">
          <FormField
            id="sign-in-email"
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <FormField
            id="sign-in-password"
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="text-sm text-muted-foreground">
        New to Ferasha?&nbsp;
        <Link href={registerHref} className="text-foreground underline underline-offset-4">
          Create an account
        </Link>
      </CardFooter>
    </Card>
  );
}
