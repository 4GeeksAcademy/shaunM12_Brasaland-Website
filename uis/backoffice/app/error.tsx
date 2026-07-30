"use client";

/**
 * Root route error boundary. Catches render/data errors from any segment that
 * doesn't define its own boundary, so a thrown error never leaves the user on a
 * blank/undefined screen. The raw error is intentionally NOT shown — only a
 * human-readable message plus a clear way forward.
 */

import { useEffect } from "react";
import ErrorState from "@/components/ui/ErrorState";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  useEffect(() => {
    // Keep diagnostics in the browser console for developers; never rendered.
    console.error(error);
  }, [error]);

  return (
    <main className="bo-page px-4 py-16">
      <div className="mx-auto max-w-2xl">
        <ErrorState
          message="Something went wrong while loading this page. You can try again, or head back home."
          onRetry={reset}
        />
      </div>
    </main>
  );
}
