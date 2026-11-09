/**
 * Signing out, everywhere it happens (header, dashboard, password change).
 *
 * Body measurements are sensitive personal data (DPDP Act), and this browser
 * may be shared: before the session ends, forget the unsent measurement
 * draft and every made-to-measure piece in the bag (each carries its
 * measurements). Ready-made pieces stay - they say nothing about anyone.
 * The local clean-up runs first, so a failed request cannot skip it.
 */

import { api } from "@/lib/api/client";
import { clearFitDraft } from "@/lib/fit-draft";
import { useCartStore } from "@/store/useCartStore";

export async function signOut(): Promise<void> {
  clearFitDraft();
  useCartStore.getState().forgetMeasurements();
  await api.session.signOut().catch(() => undefined);
}
