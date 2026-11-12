"use client";

import { useState } from "react";
import type { z } from "zod";

import { fieldIssues } from "@/lib/auth-validation";

/**
 * Form state with "reward early, punish late" validation, the pattern the
 * best sign-up flows use:
 * - an error first appears when you leave a field (never while typing it);
 * - once shown, it updates as you type and clears the moment it is fixed;
 * - submitting checks everything and returns the first bad field so the
 *   caller can move focus there.
 * Server errors (DRF's `{field: [msg]}`) share the same map via setErrors.
 */
export function useValidatedForm<T extends Record<string, unknown>>(schema: z.ZodType, initial: T) {
  const [values, setValues] = useState<T>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const showIssue = (name: string, next: T) => {
    const message = fieldIssues(schema, next)[name];
    setErrors((current) => {
      const updated = { ...current };
      if (message) updated[name] = message;
      else delete updated[name];
      return updated;
    });
  };

  function set<K extends keyof T & string>(name: K, value: T[K]) {
    const next = { ...values, [name]: value };
    setValues(next);
    if (name in errors) showIssue(name, next);
  }

  /** On blur. Leaving an empty field you never typed in is not a mistake yet. */
  function touch(name: keyof T & string) {
    const raw = values[name];
    if (raw !== "" && raw !== undefined) showIssue(name, values);
  }

  /** Check everything; returns the first invalid field (in form order), or null. */
  function validateAll(): string | null {
    const issues = fieldIssues(schema, values);
    setErrors(issues);
    return Object.keys(values).find((name) => name in issues) ?? Object.keys(issues)[0] ?? null;
  }

  return { values, errors, set, touch, validateAll, setErrors };
}
