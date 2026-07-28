"use client";

/**
 * Shared loading indicator for async views.
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
      className={`bo-loading ${className}`.trim()}
    >
      <span aria-hidden="true" className="bo-spinner" />
      <span>{label}</span>
    </div>
  );
}
