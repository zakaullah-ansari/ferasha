import type { ComponentProps, ReactNode } from "react";

import { PasswordInput } from "@/components/account/PasswordInput";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

interface FormFieldProps extends Omit<ComponentProps<typeof Input>, "id"> {
  readonly id: string;
  readonly label: string;
  /** Help shown under the input and read with it (e.g. a password rule). */
  readonly description?: ReactNode;
  /** A small link beside the label, e.g. "Forgot password?". */
  readonly labelAction?: ReactNode;
  /** Server or client validation message; wired to the input for screen readers. */
  readonly error?: string;
}

/**
 * Label + input + help + error, with the accessibility wiring done once.
 * `type="password"` gets the show/hide toggle everywhere, from one place.
 */
export function FormField({ id, label, description, labelAction, error, type, ...inputProps }: FormFieldProps) {
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [descriptionId, errorId].filter(Boolean).join(" ") || undefined;
  const control = {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    ...inputProps,
  };
  return (
    <Field data-invalid={error ? true : undefined}>
      {labelAction ? (
        <div className="flex items-center justify-between gap-2">
          <FieldLabel htmlFor={id}>{label}</FieldLabel>
          {labelAction}
        </div>
      ) : (
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
      )}
      {type === "password" ? <PasswordInput {...control} /> : <Input type={type} {...control} />}
      {description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
      {error && (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </Field>
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
