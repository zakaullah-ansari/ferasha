"use client";

import {
  ExternalLink,
  Images,
  LayoutDashboard,
  LogOut,
  MessageSquareQuote,
  Plus,
  Shirt,
  ShoppingBag,
  Store,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { ADMIN_LINKS } from "@/lib/admin-links";
import type { SessionUser } from "@/lib/api/types";
import { signOut as endSession } from "@/lib/sign-out";

const WORK = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "Orders", href: "/dashboard/orders", icon: ShoppingBag },
] as const;

/** Editing lives in the Django admin (one set of forms, one set of rules); these open it. */
const EDIT = [
  { label: "Products", href: ADMIN_LINKS.products, icon: Shirt },
  { label: "Add a product", href: ADMIN_LINKS.addProduct, icon: Plus },
  { label: "Reviews to moderate", href: ADMIN_LINKS.pendingReviews, icon: MessageSquareQuote },
  { label: "Photos to check", href: ADMIN_LINKS.photosToReview, icon: Images },
  { label: "Everything else", href: ADMIN_LINKS.home, icon: ExternalLink },
] as const;

export function DashboardSidebar({ user }: { user: Pick<SessionUser, "full_name" | "email"> }) {
  const pathname = usePathname();
  const router = useRouter();
  const { setOpenMobile } = useSidebar();
  // On a phone the menu is a sheet; a link moves within the app, so close it once the page changes.
  useEffect(() => setOpenMobile(false), [pathname, setOpenMobile]);
  const isActive = (href: string) => (href === "/dashboard" ? pathname === href : pathname.startsWith(href));

  async function signOut() {
    await endSession();
    router.push("/");
    router.refresh();
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <Link href="/dashboard" className="px-2 py-1.5 group-data-[collapsible=icon]:hidden">
          <span className="block font-display text-2xl leading-none">Ferasha</span>
          <span className="mt-1 block text-[0.65rem] tracking-[0.2em] text-muted-foreground uppercase">Atelier dashboard</span>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Today</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {WORK.map(({ label, href, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton isActive={isActive(href)} tooltip={label} render={<Link href={href} />}>
                    <Icon />
                    <span>{label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Edit in Django admin</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {EDIT.map(({ label, href, icon: Icon }) => (
                <SidebarMenuItem key={label}>
                  <SidebarMenuButton
                    tooltip={label}
                    render={<a href={href} target="_blank" rel="noreferrer" aria-label={`${label} (opens the admin in a new tab)`} />}
                  >
                    <Icon />
                    <span>{label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="View the shop" render={<Link href="/" />}>
              <Store />
              <span>View the shop</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Sign out" onClick={signOut}>
              <LogOut />
              <span className="flex min-w-0 flex-col text-left leading-tight">
                <span>Sign out</span>
                <span className="truncate text-xs text-muted-foreground">{user.full_name || user.email}</span>
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
