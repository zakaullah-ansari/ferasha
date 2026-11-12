import { LayoutDashboard } from "lucide-react";
import Link from "next/link";

import { LinkPagination } from "@/components/LinkPagination";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { OrderSummary, SessionUser } from "@/lib/api/types";

import { OrderHistory } from "./OrderHistory";
import { PasswordForm } from "./PasswordForm";
import { ProfileForm } from "./ProfileForm";
import { VerifyEmailNudge } from "./VerifyEmailNudge";

interface AccountViewProps {
  readonly user: SessionUser;
  readonly orders: readonly OrderSummary[];
  readonly page: number;
  readonly pageCount: number;
}

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

/** The customer's own corner: their orders first, then their details. */
export function AccountView({ user, orders, page, pageCount }: AccountViewProps) {
  const firstName = user.full_name.split(" ")[0] || user.full_name;
  return (
    <div className="mx-auto max-w-6xl px-5 pt-10 pb-24">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.25em] text-muted-foreground uppercase">Your account</p>
          <h1 className="mt-3 font-display text-display-sm leading-tight">Hello, {firstName}</h1>
        </div>
        {user.is_back_office && (
          <Link href="/dashboard" className={buttonVariants({ variant: "outline" })}>
            <LayoutDashboard data-icon="inline-start" />
            Atelier dashboard
          </Link>
        )}
      </div>

      {user.email_verified === false && (
        <div className="mt-6">
          <VerifyEmailNudge email={user.email} />
        </div>
      )}

      <div className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Section title="Your orders" description="Follow each one from the atelier to your door">
          <OrderHistory orders={orders} />
          <div className="mt-4">
            <LinkPagination page={page} pageCount={pageCount} href={(target) => (target > 1 ? `/account?page=${target}` : "/account")} />
          </div>
        </Section>
        <div className="grid content-start gap-6">
          <Section title="Your details">
            <ProfileForm user={user} />
          </Section>
          <Section title="Password">
            <PasswordForm />
          </Section>
        </div>
      </div>
    </div>
  );
}
