import type { ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FormFieldProps extends Omit<ComponentProps<typeof Input>, "id"> {
  readonly id: string;
  readonly label: string;
  /** Server or client validation message; wired to the input for screen readers. */
  readonly error?: string;
}

/** Label + shadcn Input + error message, with the accessibility wiring done once. */
export function FormField({ id, label, error, ...inputProps }: FormFieldProps) {
  const errorId = `${id}-error`;
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {error && (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

/** First message per field from a DRF validation body (`{"field": ["msg"]}`). */
export function fieldErrors(body: Readonly<Record<string, unknown>> | undefined): Record<string, string> {
  if (!body) return {};
  return Object.fromEntries(
    Object.entries(body)
      .filter(([key]) => key !== "detail")
      .map(([key, value]) => [key, Array.isArray(value) ? String(value[0]) : String(value)]),
  );
}
