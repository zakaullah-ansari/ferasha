import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/account/ForgotPasswordForm";

export const metadata: Metadata = { title: "Forgot your password", robots: { index: false } };

export default function ForgotPasswordPage() {
  return (
    <div className="mx-auto flex max-w-6xl justify-center px-5 py-16">
      <ForgotPasswordForm />
    </div>
  );
}
