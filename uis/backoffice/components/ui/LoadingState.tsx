/**
 * Shared loading indicator for async views.
 *
 * Renders a small spinner plus an accessible label so every data-fetching view
 * has a consistent "loading" state (see context-9 error-handling roadmap).
 */

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export default function LoadingState({
  label = "Loading...",
  className = "",
}: LoadingStateProps): React.JSX.Element {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center gap-3 rounded-xl border border-stone-700 bg-stone-900/80 px-4 py-3 text-sm text-stone-300 ${className}`}
    >
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-stone-600 border-t-amber-300"
      />
      <span>{label}</span>
    </div>
  );
}
