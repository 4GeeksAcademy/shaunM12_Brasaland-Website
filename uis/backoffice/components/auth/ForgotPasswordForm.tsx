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
    <div className="w-full max-w-md space-y-6 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 shadow-2xl shadow-black/30">
      <div className="space-y-1 text-center">
        <p className="text-sm uppercase tracking-[0.16em] text-amber-300">
          Brasaland Backoffice
        </p>
        <h1 className="text-2xl font-extrabold text-amber-100">
          Forgot password
        </h1>
      </div>

      {submitted ? (
        <div className="space-y-4 text-center">
          <p
            role="status"
            className="rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200"
          >
            {CONFIRMATION}
          </p>
          {rateLimited ? (
            <p className="text-sm text-amber-200">
              You&apos;ve made several requests recently — please wait a little
              while before trying again.
            </p>
          ) : null}
          <Link
            href="/login"
            className="inline-block font-semibold text-amber-300 hover:text-amber-200"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <p className="text-sm text-stone-300">
            Enter your account email and we&apos;ll send you a link to reset your
            password.
          </p>

          <label className="block text-sm text-stone-200">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Sending..." : "Send reset link"}
          </button>

          <p className="text-center text-sm text-stone-400">
            Remembered it?{" "}
            <Link
              href="/login"
              className="font-semibold text-amber-300 hover:text-amber-200"
            >
              Sign in
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
