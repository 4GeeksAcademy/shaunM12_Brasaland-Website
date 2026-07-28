import { Suspense } from "react";

import LoginForm from "@/components/auth/LoginForm";

export default function LoginPage(): React.JSX.Element {
  return (
    <main className="bo-page bo-page-centered">
      <Suspense
        fallback={<p className="text-sm bo-muted">Loading...</p>}
      >
        <LoginForm />
      </Suspense>
    </main>
  );
}
