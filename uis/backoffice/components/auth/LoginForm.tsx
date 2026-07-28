"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/context/AuthProvider";
import { HOME_PATH } from "@/lib/auth-config";

function safeNext(raw: string | null): string {
  // Only allow same-app relative paths to avoid open-redirects.
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) {
    return raw;
  }
  return HOME_PATH;
}

export default function LoginForm(): React.JSX.Element {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const justReset = searchParams.get("reset") === "success";

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace(safeNext(searchParams.get("next")));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign in failed");
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6 bo-auth-card">
      <div className="space-y-1 text-center">
        <p className="bo-eyebrow">
          Brasaland Backoffice
        </p>
        <h1 className="bo-title text-2xl md:text-3xl">Sign in</h1>
      </div>

      {justReset ? (
        <p
          role="status"
          className="bo-alert-success"
        >
          Your password has been reset. Please sign in with your new password.
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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

        <label className="block text-sm bo-fg-secondary">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
          />
        </label>

        {error ? (
          <p
            role="alert"
            className="bo-alert-error rounded-md px-3 py-2 text-sm"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="bo-btn-primary w-full py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
        >
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="text-center text-sm bo-muted">
        <Link
          href="/forgot-password"
          className="font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]"
        >
          Forgot your password?
        </Link>
      </p>

      <p className="text-center text-sm bo-muted">
        No account?{" "}
        <Link href="/register" className="font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]">
          Create one
        </Link>
      </p>
    </div>
  );
}
