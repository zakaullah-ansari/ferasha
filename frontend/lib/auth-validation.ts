/**
 * Sign-in and registration rules, checked in the browser for instant,
 * field-by-field feedback. Django stays the authority (it also runs the
 * common-password list and the breached-password check, which cannot run
 * here); these mirror its rules exactly so the browser never accepts what
 * the server will refuse, nor refuses what it would accept.
 *
 * Mirrors: users.RegistrationSerializer and AUTH_PASSWORD_VALIDATORS.
 */

import { z } from "zod";

export const PASSWORD_MIN = 10;
const NAME_MAX = 180;
const EMAIL_MAX = 254;

const email = z
  .string()
  .trim()
  .min(1, "Enter your email address.")
  .max(EMAIL_MAX, "That email address is too long.")
  .pipe(z.email("Enter a valid email address, like name@example.com."));

export interface PasswordRule {
  readonly id: "length" | "numeric";
  readonly label: string;
  readonly met: boolean;
}

/**
 * The rules shown as a live checklist under the password: exactly the two
 * Django checks that can run in a browser. The rest (common passwords,
 * similarity to your details, known breaches) answer from the server.
 */
export function passwordRules(password: string): PasswordRule[] {
  return [
    { id: "length", label: `At least ${PASSWORD_MIN} characters`, met: password.length >= PASSWORD_MIN },
    { id: "numeric", label: "Not only numbers", met: password.length > 0 && !/^\d+$/.test(password) },
  ];
}

const RULE_MESSAGES: Record<PasswordRule["id"], string> = {
  length: `Use at least ${PASSWORD_MIN} characters.`,
  numeric: "Use letters or symbols too, not only numbers.",
};

/**
 * Checked on the field itself, not the whole form: an object-level refine
 * would stay silent until every other field was valid.
 */
const newPassword = z
  .string()
  .min(1, "Choose a password.")
  .superRefine((password, context) => {
    const broken = passwordRules(password).find((rule) => !rule.met);
    if (broken) context.addIssue({ code: "custom", message: RULE_MESSAGES[broken.id] });
  });

export const registerSchema = z.object({
  full_name: z.string().trim().min(1, "Enter your full name.").max(NAME_MAX, "That name is too long."),
  email,
  password: newPassword,
  accept_terms: z.literal(true, { error: "Please accept the terms to create an account." }),
});

export const signInSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password."),
});

/** First message per field, keyed like DRF's errors so both can share one map. */
export function fieldIssues(schema: z.ZodType, values: unknown): Record<string, string> {
  const result = schema.safeParse(values);
  if (result.success) return {};
  const issues: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = String(issue.path[0] ?? "form");
    issues[key] ??= issue.message;
  }
  return issues;
}

/* ------------------------------------------------------- email typo help */

const COMMON_DOMAINS = [
  "gmail.com",
  "yahoo.com",
  "yahoo.co.in",
  "hotmail.com",
  "outlook.com",
  "icloud.com",
  "rediffmail.com",
  "live.com",
] as const;

function distance(a: string, b: string): number {
  // Levenshtein with one rolling row; inputs are a few characters long.
  const row = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    let diagonal = row[0]!;
    row[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      const above = row[j]!;
      row[j] = Math.min(above + 1, row[j - 1]! + 1, diagonal + (a[i - 1] === b[j - 1] ? 0 : 1));
      diagonal = above;
    }
  }
  return row[b.length]!;
}

/**
 * "ayesha@gmial.com" -> "ayesha@gmail.com". Only near-misses of the most
 * common providers, never a rewrite: the person decides.
 */
export function suggestEmail(value: string): string | null {
  const trimmed = value.trim().toLowerCase();
  const at = trimmed.lastIndexOf("@");
  if (at < 1) return null;
  const domain = trimmed.slice(at + 1);
  if (domain.length < 4 || (COMMON_DOMAINS as readonly string[]).includes(domain)) return null;
  let best: { domain: string; score: number } | null = null;
  for (const candidate of COMMON_DOMAINS) {
    const score = distance(domain, candidate);
    if (score <= 2 && (!best || score < best.score)) best = { domain: candidate, score };
  }
  return best ? `${trimmed.slice(0, at)}@${best.domain}` : null;
}
