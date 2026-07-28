import { Suspense } from "react";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export default function ForgotPasswordPage(): React.JSX.Element {
  return (
    <main className="bo-page bo-page-centered">
      <Suspense fallback={<p className="text-sm bo-muted">Loading...</p>}>
        <ForgotPasswordForm />
      </Suspense>
    </main>
  );
}
