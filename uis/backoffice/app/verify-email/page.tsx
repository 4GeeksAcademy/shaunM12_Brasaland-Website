import { Suspense } from "react";

import VerifyEmailPanel from "@/components/auth/VerifyEmailPanel";

export default function VerifyEmailPage(): React.JSX.Element {
  return (
    <main className="bo-page bo-page-centered">
      <Suspense
        fallback={<p className="text-sm bo-muted">Loading...</p>}
      >
        <VerifyEmailPanel />
      </Suspense>
    </main>
  );
}
