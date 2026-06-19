import { Suspense } from "react";

import LoginForm from "@/components/auth/LoginForm";

export default function LoginPage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10">
      <Suspense
        fallback={<p className="text-sm text-stone-300">Loading...</p>}
      >
        <LoginForm />
      </Suspense>
    </main>
  );
}
