const LINK = "text-foreground underline underline-offset-4 hover:text-primary";

/**
 * "the terms of use and the privacy policy", linked, opening in a new tab so
 * a half-filled form is not lost. Shared by the register checkbox and the
 * line beside "Continue with Google" (which accepts them on the person's behalf).
 */
export function TermsLinks() {
  return (
    <>
      the{" "}
      <a href="/policies/terms" target="_blank" rel="noreferrer" className={LINK}>
        terms of use
      </a>{" "}
      and the{" "}
      <a href="/policies/privacy" target="_blank" rel="noreferrer" className={LINK}>
        privacy policy
      </a>
    </>
  );
}
