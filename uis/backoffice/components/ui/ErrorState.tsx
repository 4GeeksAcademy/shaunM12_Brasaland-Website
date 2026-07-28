"use client";

/**
 * Shared error state for async views.
 */

import Link from "next/link";
import { HOME_PATH } from "@/lib/auth-config";

interface ErrorStateProps {
  message?: string | null;
  onRetry?: () => void;
  homeHref?: string;
  showHomeLink?: boolean;
  supportEmail?: string;
  className?: string;
}

const DEFAULT_MESSAGE =
  "Something went wrong while loading this content. Please try again.";

export default function ErrorState({
  message,
  onRetry,
  homeHref = HOME_PATH,
  showHomeLink = true,
  supportEmail = "support@brasaland.com",
  className = "",
}: ErrorStateProps): React.JSX.Element {
  return (
    <div
      role="alert"
      className={`bo-alert-error space-y-3 ${className}`.trim()}
    >
      <p className="font-semibold">{message?.trim() ? message : DEFAULT_MESSAGE}</p>

      <div className="flex flex-wrap items-center gap-3">
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="bo-btn-primary px-4 py-1.5 normal-case tracking-normal"
          >
            Try again
          </button>
        ) : null}

        {showHomeLink ? (
          <Link href={homeHref} className="bo-btn-secondary px-4 py-1.5 normal-case tracking-normal">
            Back to home
          </Link>
        ) : null}

        <a
          href={`mailto:${supportEmail}`}
          className="text-xs font-medium text-[color:var(--bo-error-muted)] underline underline-offset-2 transition hover:text-[color:var(--bo-error-fg)]"
        >
          Contact support
        </a>
      </div>
    </div>
  );
}
