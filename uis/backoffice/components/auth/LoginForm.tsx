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
    <div className="w-full max-w-md space-y-6 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 shadow-2xl shadow-black/30">
      <div className="space-y-1 text-center">
        <p className="text-sm uppercase tracking-[0.16em] text-amber-300">
          Brasaland Backoffice
        </p>
        <h1 className="text-2xl font-extrabold text-amber-100">Sign in</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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

        <label className="block text-sm text-stone-200">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
          />
        </label>

        {error ? (
          <p
            role="alert"
            className="rounded-md bg-rose-500/10 px-3 py-2 text-sm text-rose-200"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="text-center text-sm text-stone-400">
        No account?{" "}
        <Link href="/register" className="font-semibold text-amber-300 hover:text-amber-200">
          Create one
        </Link>
      </p>
    </div>
  );
}
