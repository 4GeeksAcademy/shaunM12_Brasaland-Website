"use client";

import { useEffect } from "react";
import ErrorState from "@/components/ui/ErrorState";

export default function RegistrationAnalyticsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-16 text-stone-100">
      <div className="mx-auto max-w-2xl">
        <ErrorState
          message="We couldn't load the registration analytics right now. Please try again."
          onRetry={reset}
        />
      </div>
    </main>
  );
}
