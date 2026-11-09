"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api/client";
import type { SessionUser } from "@/lib/api/types";

/** Name and mobile. The email is the sign-in, so it is shown but not edited here. */
export function ProfileForm({ user }: { user: Pick<SessionUser, "full_name" | "email" | "phone"> }) {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: user.full_name, phone: user.phone ?? "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "failed">("idle");

  const field = (name: keyof typeof form) => ({
    value: form[name],
    error: errors[name],
    onChange: (event: { target: { value: string } }) => {
      setForm((current) => ({ ...current, [name]: event.target.value }));
      setStatus("idle");
    },
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("saving");
    setErrors({});
    try {
      await api.session.updateProfile({ full_name: form.full_name.trim(), phone: form.phone.trim() });
      setStatus("saved");
      router.refresh();
    } catch (caught) {
      setErrors(caught instanceof ApiError && caught.status === 400 ? fieldErrors(caught.body) : {});
      setStatus("failed");
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <FormField id="profile-name" label="Full name" autoComplete="name" required {...field("full_name")} />
      <FormField id="profile-phone" label="Mobile" type="tel" autoComplete="tel" {...field("phone")} />
      <div className="grid gap-1 text-sm">
        <span className="text-muted-foreground">Email</span>
        <span>{user.email}</span>
      </div>
      <div className="flex items-center gap-4">
        <Button type="submit" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : "Save details"}
        </Button>
        <p role="status" className="text-sm text-muted-foreground">
          {status === "saved" && "Saved."}
          {status === "failed" && <span className="text-destructive">Your details could not be saved.</span>}
        </p>
      </div>
    </form>
  );
}
