/** How review answers read on the page; one place for the summary, the list and the form. */

import type { FitFeedback, ReviewSummary } from "@/lib/api/types";

export const FIT_LABELS: Readonly<Record<FitFeedback, string>> = {
  ran_small: "Runs small",
  true_to_size: "True to size",
  ran_large: "Runs large",
};

/** The fit most reviewers report, if any did: "Most say: true to size". */
export function usualFit(summary: ReviewSummary): FitFeedback | null {
  const entries = Object.entries(summary.fit) as [FitFeedback, number][];
  const [top, count] = entries.reduce((best, entry) => (entry[1] > best[1] ? entry : best), entries[0]!);
  return count > 0 ? top : null;
}

/** Share of reviewers who answered the coverage question and said yes, as a whole percent. */
export function coverageAsDescribed(summary: ReviewSummary): number | null {
  const { yes, no } = summary.modesty_as_described;
  return yes + no > 0 ? Math.round((yes / (yes + no)) * 100) : null;
}
