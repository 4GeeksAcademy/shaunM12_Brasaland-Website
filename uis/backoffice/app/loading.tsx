/**
 * Root route loading fallback, shown while a server component segment streams.
 * Guarantees a visible "loading" state for navigations that fetch on the server.
 */

import LoadingState from "@/components/ui/LoadingState";

export default function AppLoading(): React.JSX.Element {
  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-16 text-stone-100">
      <div className="mx-auto max-w-2xl">
        <LoadingState label="Loading..." />
      </div>
    </main>
  );
}
