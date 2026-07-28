"use client";

import Link from "next/link";
import { useState } from "react";

import { AuthApiError, forgotPassword } from "@/lib/auth-api";

const CONFIRMATION =
  "If that address is registered, you'll receive a link shortly.";

export default function ForgotPasswordForm(): React.JSX.Element {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rateLimited, setRateLimited] = useState(false);

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (caught) {
      // Surface only the rate limit; for anything else still show the generic
      // confirmation so we never reveal whether the address exists.
      if (caught instanceof AuthApiError && caught.status === 429) {
        setRateLimited(true);
      }
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6 bo-auth-card">
      <div className="space-y-1 text-center">
        <p className="bo-eyebrow">
          Brasaland Backoffice
        </p>
        <h1 className="bo-title text-2xl md:text-3xl">
          Forgot password
        </h1>
      </div>

      {submitted ? (
        <div className="space-y-4 text-center">
          <p
            role="status"
            className="bo-alert-success"
          >
            {CONFIRMATION}
          </p>
          {rateLimited ? (
            <p className="text-sm text-[color:var(--bo-accent-muted)]">
              You&apos;ve made several requests recently — please wait a little
              while before trying again.
            </p>
          ) : null}
          <Link
            href="/login"
            className="inline-block font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <p className="text-sm bo-muted">
            Enter your account email and we&apos;ll send you a link to reset your
            password.
          </p>

          <label className="block text-sm bo-fg-secondary">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="bo-btn-primary w-full py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
          >
            {submitting ? "Sending..." : "Send reset link"}
          </button>

          <p className="text-center text-sm bo-muted">
            Remembered it?{" "}
            <Link
              href="/login"
              className="font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]"
            >
              Sign in
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
