"use client";

import { ShoppingBag, User } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import type { SessionUser } from "@/lib/api/types";
import { selectItemCount, useBagHydrated, useCartStore } from "@/store/useCartStore";

/**
 * The header's client island: account state and the bag button.
 *
 * Account state is fetched rather than read from a cookie on the server, so
 * the layout (and with it every catalogue page) stays statically renderable.
 */
export function HeaderActions() {
  const router = useRouter();
  const pathname = usePathname();
  const hydrated = useBagHydrated();
  const count = useCartStore(selectItemCount);
  const openBag = useCartStore((state) => state.setDrawerOpen);
  // undefined = still checking; null = guest.
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined);

  // Re-checked on every navigation: the header persists across client-side
  // route changes, so signing in or registering would otherwise leave it
  // showing "Sign in" until a full reload.
  useEffect(() => {
    let cancelled = false;
    api.session
      .me()
      .then((me) => !cancelled && setUser(me))
      .catch(() => !cancelled && setUser(null));
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  async function signOut() {
    await api.session.signOut().catch(() => undefined);
    setUser(null);
    router.refresh();
  }

  const shownCount = hydrated ? count : 0;

  return (
    <div className="flex items-center gap-2">
      {user === null && (
        <Link
          href="/account/sign-in"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <User className="size-4" aria-hidden="true" />
          Sign in
        </Link>
      )}
      {user && (
        <div className="flex items-center gap-3 text-sm">
          <span className="hidden text-muted-foreground sm:inline">
            {user.full_name.split(" ")[0] || user.email}
          </span>
          <Button variant="ghost" size="sm" onClick={signOut}>
            Sign out
          </Button>
        </div>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        aria-label={shownCount > 0 ? `Open bag, ${shownCount} items` : "Open bag"}
        onClick={() => openBag(true)}
      >
        <ShoppingBag />
        {shownCount > 0 && (
          <Badge className="absolute -top-1 -right-1 h-5 min-w-5 px-1 tabular-nums" aria-hidden="true">
            {shownCount}
          </Badge>
        )}
      </Button>
    </div>
  );
}
