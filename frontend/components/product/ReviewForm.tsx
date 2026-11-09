"use client";

import { Star } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useEffect, useId, useState } from "react";

import { FormField, fieldErrors } from "@/components/FormField";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api/client";
import type { FitFeedback, SessionUser } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { FIT_LABELS } from "@/lib/reviews";

const EMPTY = { rating: 0, title: "", body: "", fit_feedback: "" as FitFeedback | "", modesty: "" as "" | "yes" | "no" };

/** The star picker: a real radio group (arrow keys, screen readers), drawn as stars. */
function StarPicker({ value, onChange }: { value: number; onChange: (rating: number) => void }) {
  const id = useId();
  return (
    <RadioGroup aria-label="Your rating" value={value ? String(value) : ""} onValueChange={(next) => onChange(Number(next))} className="flex gap-1">
      {[1, 2, 3, 4, 5].map((step) => (
        <div key={step}>
          <RadioGroupItem id={`${id}-${step}`} value={String(step)} className="sr-only" />
          <Label
            htmlFor={`${id}-${step}`}
            className="cursor-pointer rounded-md p-1 peer-focus-visible:ring-[3px] peer-focus-visible:ring-ring/50"
          >
            <Star aria-hidden="true" className={cn("size-7 text-gold-500", step <= value && "fill-current")} />
            <span className="sr-only">
              {step} {step === 1 ? "star" : "stars"}
            </span>
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}

function Choice<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T | "";
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <fieldset className="grid gap-2">
      <legend className="mb-2 text-sm font-medium">{label}</legend>
      <RadioGroup value={value} onValueChange={(next) => onChange(next as T)} className="flex flex-wrap gap-x-5 gap-y-2">
        {options.map((option) => (
          <div key={option.value} className="flex items-center gap-2">
            <RadioGroupItem id={`${id}-${option.value}`} value={option.value} />
            <Label htmlFor={`${id}-${option.value}`} className="font-normal">
              {option.label}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </fieldset>
  );
}

/**
 * Writing a review. Everyone signed in may review; the server marks it a
 * verified purchase when there is a delivered order, and nobody sees it
 * until the atelier has read it.
 */
export function ReviewForm({ productId, productSlug }: { productId: string; productSlug: string }) {
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<"editing" | "sending" | "sent">("editing");

  useEffect(() => {
    api.session.me().then(setUser).catch(() => setUser(null));
  }, []);

  if (user === undefined) return null;
  if (user === null) {
    return (
      <Link href={`/account/sign-in?next=${encodeURIComponent(`/products/${productSlug}#reviews`)}`} className={buttonVariants({ variant: "outline" })}>
        Sign in to write a review
      </Link>
    );
  }
  if (state === "sent") {
    return (
      <p role="status" className="rounded-2xl bg-primary/10 px-4 py-3 text-sm text-primary">
        Thank you. Your review will appear here once the atelier has read it.
      </p>
    );
  }
  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        Write a review
      </Button>
    );
  }

  const text = (name: "title" | "body") => (event: { target: { value: string } }) => setForm((current) => ({ ...current, [name]: event.target.value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (form.rating === 0) {
      setErrors({ rating: "Choose from one to five stars." });
      return;
    }
    setState("sending");
    setErrors({});
    setError(null);
    try {
      await api.createReview({
        product: productId,
        rating: form.rating,
        title: form.title.trim(),
        body: form.body.trim(),
        fit_feedback: form.fit_feedback,
        modesty_as_described: form.modesty === "" ? null : form.modesty === "yes",
      });
      setState("sent");
    } catch (caught) {
      const body = caught instanceof ApiError && caught.status === 400 ? fieldErrors(caught.body) : {};
      // "Already reviewed" comes back against the product.
      if (body.product) setError(body.product);
      else if (Object.keys(body).length > 0) setErrors(body);
      else setError("Your review could not be sent just now. Please try again.");
      setState("editing");
    }
  }

  return (
    <form onSubmit={submit} className="grid max-w-xl gap-5 rounded-2xl border p-5">
      <div className="grid gap-1">
        <StarPicker value={form.rating} onChange={(rating) => setForm((current) => ({ ...current, rating }))} />
        {errors.rating && <p className="text-sm text-destructive">{errors.rating}</p>}
      </div>
      <FormField id="review-title" label="Title (optional)" maxLength={140} value={form.title} error={errors.title} onChange={text("title")} />
      <div className="grid gap-2">
        <Label htmlFor="review-body">Your review</Label>
        <Textarea id="review-body" rows={4} value={form.body} onChange={text("body")} placeholder="How did it fit, feel and wear?" />
      </div>
      <Choice
        label="How was the fit?"
        options={(Object.keys(FIT_LABELS) as FitFeedback[]).map((value) => ({ value, label: FIT_LABELS[value] }))}
        value={form.fit_feedback}
        onChange={(fit_feedback) => setForm((current) => ({ ...current, fit_feedback }))}
      />
      <Choice
        label="Was the coverage as described?"
        options={[
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
        ]}
        value={form.modesty}
        onChange={(modesty) => setForm((current) => ({ ...current, modesty }))}
      />
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex gap-3">
        <Button type="submit" disabled={state === "sending"}>
          {state === "sending" ? "Sending…" : "Send review"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">Only your first name is shown. Reviews appear once the atelier has read them.</p>
    </form>
  );
}
