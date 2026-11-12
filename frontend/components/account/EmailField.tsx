"use client";

import { useState } from "react";

import { FormField } from "@/components/FormField";
import { suggestEmail } from "@/lib/auth-validation";

/**
 * The email box for sign-in and registration, with typo help: leave
 * "ayesha@gmial.com" and it offers "ayesha@gmail.com" as one tap. It only
 * suggests; nothing is changed unless the person accepts.
 */
export function EmailField({
  id,
  value,
  error,
  onValue,
  onBlur,
  autoFocus,
}: {
  readonly id: string;
  readonly value: string;
  readonly error?: string;
  readonly onValue: (value: string) => void;
  readonly onBlur: () => void;
  readonly autoFocus?: boolean;
}) {
  // Only once they have left the box: mid-typing "gmail.co" is not a typo yet.
  const [left, setLeft] = useState(false);
  const suggestion = left && !error ? suggestEmail(value) : null;
  return (
    <FormField
      id={id}
      label="Email"
      type="email"
      inputMode="email"
      autoComplete="email"
      autoCapitalize="none"
      spellCheck={false}
      placeholder="name@example.com"
      required
      autoFocus={autoFocus}
      value={value}
      error={error}
      onChange={(event) => {
        setLeft(false);
        onValue(event.target.value);
      }}
      onBlur={() => {
        setLeft(true);
        onBlur();
      }}
      description={
        suggestion ? (
          <span role="status">
            Did you mean{" "}
            <button
              type="button"
              className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
              onClick={() => onValue(suggestion)}
            >
              {suggestion}
            </button>
            ?
          </span>
        ) : undefined
      }
    />
  );
}
