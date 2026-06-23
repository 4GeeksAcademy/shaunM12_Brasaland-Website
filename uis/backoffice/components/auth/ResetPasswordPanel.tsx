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
    "mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20";

  if (!token) {
    return (
      <div className="w-full max-w-md space-y-5 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 text-center shadow-2xl shadow-black/30">
        <h1 className="text-2xl font-extrabold text-amber-100">Reset password</h1>
        <p className="text-sm text-rose-200">
          This reset link is missing its token.
        </p>
        <Link
          href="/forgot-password"
          className="inline-block font-semibold text-amber-300 hover:text-amber-200"
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
    <div className="w-full max-w-md space-y-6 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 shadow-2xl shadow-black/30">
      <div className="space-y-1 text-center">
        <p className="text-sm uppercase tracking-[0.16em] text-amber-300">
          Brasaland Backoffice
        </p>
        <h1 className="text-2xl font-extrabold text-amber-100">
          Choose a new password
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <label className="block text-sm text-stone-200">
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

        <label className="block text-sm text-stone-200">
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
            className="space-y-2 rounded-md bg-rose-500/10 px-3 py-2 text-sm text-rose-200"
          >
            <p>{error}</p>
            <Link
              href="/forgot-password"
              className="inline-block font-semibold text-amber-300 hover:text-amber-200"
            >
              Request a new link
            </Link>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Reset password"}
        </button>
      </form>
    </div>
  );
}
