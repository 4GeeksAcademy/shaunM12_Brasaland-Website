import { Suspense } from "react";

import ResetPasswordPanel from "@/components/auth/ResetPasswordPanel";

export default function ResetPasswordPage(): React.JSX.Element {
  return (
    <main className="bo-page bo-page-centered">
      <Suspense fallback={<p className="text-sm bo-muted">Loading...</p>}>
        <ResetPasswordPanel />
      </Suspense>
    </main>
  );
}
