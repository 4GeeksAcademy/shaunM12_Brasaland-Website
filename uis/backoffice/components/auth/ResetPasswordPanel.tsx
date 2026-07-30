"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { resetPassword } from "@/lib/auth-api";

const MIN_PASSWORD_LENGTH = 8;

export default function ResetPasswordPanel(): React.JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const inputClass =
    "mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]";

  if (!token) {
    return (
      <div className="bo-auth-card space-y-5 text-center">
        <h1 className="bo-title text-2xl md:text-3xl">Reset password</h1>
        <p className="text-sm text-[color:var(--bo-error-fg)]">
          This reset link is missing its token.
        </p>
        <Link
          href="/forgot-password"
          className="inline-block font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, password);
      router.replace("/login?reset=success");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not reset your password.",
      );
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
          Choose a new password
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <label className="block text-sm bo-fg-secondary">
          New password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
            className={inputClass}
          />
        </label>

        <label className="block text-sm bo-fg-secondary">
          Confirm new password
          <input
            type="password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
            autoComplete="new-password"
            className={inputClass}
          />
        </label>

        {error ? (
          <div
            role="alert"
            className="space-y-2 bo-alert-error rounded-md px-3 py-2 text-sm"
          >
            <p>{error}</p>
            <Link
              href="/forgot-password"
              className="inline-block font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]"
            >
              Request a new link
            </Link>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="bo-btn-primary w-full py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
        >
          {submitting ? "Saving..." : "Reset password"}
        </button>
      </form>
    </div>
  );
}
