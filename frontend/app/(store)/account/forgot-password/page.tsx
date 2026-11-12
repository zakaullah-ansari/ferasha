import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/account/ForgotPasswordForm";
import { AuthPage } from "@/components/account/AuthCard";

export const metadata: Metadata = { title: "Forgot your password", robots: { index: false } };

export default function ForgotPasswordPage() {
  return (
    <AuthPage>
      <ForgotPasswordForm />
    </AuthPage>
  );
}
