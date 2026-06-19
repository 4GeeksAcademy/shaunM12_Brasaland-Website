import { Suspense } from "react";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export default function ForgotPasswordPage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10">
      <Suspense fallback={<p className="text-sm text-stone-300">Loading...</p>}>
        <ForgotPasswordForm />
      </Suspense>
    </main>
  );
}
