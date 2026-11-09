/**
 * The fit drawer's unsent measurements, kept in this browser so a shopper
 * does not lose them mid-entry. Body measurements are sensitive personal
 * data (DPDP Act): the draft is cleared on submit and on sign-out, so the
 * next person at a shared computer never finds them.
 */
export const FIT_DRAFT_KEY = "ferasha:fit-draft:v1";

export function clearFitDraft(): void {
  try {
    window.localStorage.removeItem(FIT_DRAFT_KEY);
  } catch {
    // Storage unavailable (private mode, server render): nothing was saved.
  }
}
