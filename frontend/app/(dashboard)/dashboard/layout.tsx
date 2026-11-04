import type { Metadata } from "next";
import { cookies } from "next/headers";

import { DashboardSidebar } from "@/components/dashboard/DashboardSidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { requireBackOffice } from "@/lib/back-office";

export const metadata: Metadata = {
  title: { default: "Dashboard", template: "%s · Ferasha dashboard" },
  robots: { index: false, follow: false },
};

/** The owner's dashboard: its own chrome, no storefront header, behind the back-office check. */
export default async function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const user = await requireBackOffice();
  // The sidebar remembers being collapsed in a cookie; read it so it does not flash open.
  const open = (await cookies()).get("sidebar_state")?.value !== "false";

  return (
    <TooltipProvider>
      <SidebarProvider defaultOpen={open}>
        <DashboardSidebar user={user} />
        <SidebarInset id="main">
          <header className="sticky top-0 z-10 flex h-14 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
            <SidebarTrigger aria-label="Toggle the menu" />
          </header>
          <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">{children}</div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
