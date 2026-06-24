"use client";

/**
 * Shared error state for async views.
 *
 * Guarantees every failed operation shows (1) a human-readable message and
 * (2) at least one clear exit: a retry action, a link home, or a support hint
 * (see context-9 error-handling roadmap). Raw stack traces / status codes must
 * be translated to friendly copy *before* being passed in as `message`.
 */

import Link from "next/link";
import { HOME_PATH } from "@/lib/auth-config";

interface ErrorStateProps {
  /** Human-readable explanation. Never a raw stack trace or status code. */
  message?: string | null;
  /** When provided, renders a "Try again" button wired to this handler. */
  onRetry?: () => void;
  /** Override the "Back to home" link target. Defaults to the app home. */
  homeHref?: string;
  /** Hide the home link when the error is shown inside an already-home view. */
  showHomeLink?: boolean;
  /** Support contact shown as a mailto fallback when retry isn't enough. */
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
      className={`space-y-3 rounded-xl border border-rose-500/40 bg-rose-950/30 px-4 py-4 text-sm text-rose-100 ${className}`}
    >
      <p className="font-semibold">{message?.trim() ? message : DEFAULT_MESSAGE}</p>

      <div className="flex flex-wrap items-center gap-3">
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-full bg-amber-300 px-4 py-1.5 text-xs font-semibold text-stone-950 transition hover:bg-amber-200"
          >
            Try again
          </button>
        ) : null}

        {showHomeLink ? (
          <Link
            href={homeHref}
            className="rounded-full border border-stone-500 px-4 py-1.5 text-xs font-semibold text-stone-200 transition hover:bg-stone-800"
          >
            Back to home
          </Link>
        ) : null}

        <a
          href={`mailto:${supportEmail}`}
          className="text-xs font-medium text-rose-200/80 underline underline-offset-2 transition hover:text-rose-100"
        >
          Contact support
        </a>
      </div>
    </div>
  );
}
