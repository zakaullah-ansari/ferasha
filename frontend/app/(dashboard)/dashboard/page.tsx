import { OverviewView } from "@/components/dashboard/OverviewView";
import type { DashboardSummary } from "@/lib/api/types";
import { getBackOffice } from "@/lib/back-office";

// Absolute: a layout's title template reaches its child routes, not its own page.
export const metadata = { title: { absolute: "Overview · Ferasha dashboard" } };

export default async function DashboardPage() {
  const summary = await getBackOffice<DashboardSummary>("/api/v1/back-office/summary/");
  return <OverviewView summary={summary} />;
}
