"use client";

import { Download, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api/client";
import { signOut } from "@/lib/sign-out";

/** Same path the proxy forwards to Django; a plain link, so the browser saves the file. */
export const EXPORT_HREF = "/api/v1/auth/me/export/";

const ERASED = ["Your name, email and phone", "Saved addresses and measurements", "Reviews and their photos", "Google sign-in link and preferences"];

/**
 * "Your data": download everything the shop holds, or close the account
 * (DPDP Act 2023 ss.11-12). Deleting asks for the password and says plainly
 * what goes and what tax law makes the shop keep.
 */
export function YourDataSection() {
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <p className="text-sm text-muted-foreground">
          Your profile, addresses, measurements, orders and reviews, as one file.
        </p>
        <a href={EXPORT_HREF} download className={buttonVariants({ variant: "outline", className: "justify-self-start" })}>
          <Download data-icon="inline-start" />
          Download my data
        </a>
      </div>
      <div className="grid gap-2 border-t pt-5">
        <p className="text-sm text-muted-foreground">Close your account and erase your details. This cannot be undone.</p>
        <DeleteAccountDialog />
      </div>
    </div>
  );
}

function DeleteAccountDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function reset(next: boolean) {
    setOpen(next);
    if (!next) {
      setPassword("");
      setFieldError(undefined);
      setError(null);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFieldError(undefined);
    setError(null);
    try {
      await api.session.deleteAccount(password);
      // The server has already revoked every session; clear this browser too.
      await signOut();
      router.replace("/account/sign-in?reason=account-deleted");
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 400) {
        setFieldError(fieldErrors(caught.body).password ?? "Please enter your password.");
      } else if (caught instanceof ApiError && caught.status === 409) {
        // Orders still in progress: the server names them.
        setError(caught.message);
      } else if (caught instanceof ApiError && caught.status === 429) {
        setError("Too many attempts. Please try again in an hour.");
      } else {
        setError("Your account could not be deleted just now. Please try again.");
      }
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogTrigger render={<Button variant="destructive" className="justify-self-start" />}>
        <Trash2 data-icon="inline-start" />
        Delete my account
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-5">
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>This cannot be undone. We will erase:</DialogDescription>
          </DialogHeader>
          <ul className="grid list-disc gap-1 pl-5 text-sm">
            {ERASED.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">
            Past orders stay on record only as long as Indian tax law requires invoices to be kept, no longer linked to
            you. Want a copy first? <a href={EXPORT_HREF} download className="font-medium text-primary underline-offset-4 hover:underline">Download your data</a>.
          </p>
          <FormField
            id="delete-account-password"
            label="Your password, to confirm it's you"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            error={fieldError}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <DialogClose render={<Button type="button" variant="outline" />}>Keep my account</DialogClose>
            <Button type="submit" variant="destructive" disabled={busy || !password}>
              {busy ? "Deleting…" : "Delete my account"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
