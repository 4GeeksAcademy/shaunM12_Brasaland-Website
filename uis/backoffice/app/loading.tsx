/**
 * Root route loading fallback, shown while a server component segment streams.
 * Guarantees a visible "loading" state for navigations that fetch on the server.
 */

import LoadingState from "@/components/ui/LoadingState";

export default function AppLoading(): React.JSX.Element {
  return (
    <main className="bo-page px-4 py-16">
      <div className="mx-auto max-w-2xl">
        <LoadingState label="Loading..." />
      </div>
    </main>
  );
}
