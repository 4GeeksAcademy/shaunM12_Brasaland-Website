"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/context/AuthProvider";
import { AuthApiError } from "@/lib/auth-api";
import { HOME_PATH } from "@/lib/auth-config";
import { parseFieldErrors } from "@/lib/api-error";

interface FieldErrors {
  name?: string;
  email?: string;
  password?: string;
  general?: string;
}

export default function RegisterForm(): React.JSX.Element {
  const { register } = useAuth();
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setErrors({});
    setSubmitting(true);
    try {
      await register(email, password, name);
      router.replace(HOME_PATH);
    } catch (caught) {
      if (caught instanceof AuthApiError) {
        if (caught.status === 422) {
          const fieldMap = parseFieldErrors(caught.body);
          setErrors({
            name: fieldMap.name,
            email: fieldMap.email,
            password: fieldMap.password,
            general: Object.keys(fieldMap).length ? undefined : caught.message,
          });
        } else if (caught.status === 400) {
          // Duplicate email is the only 400 from /auth/register.
          setErrors({ email: caught.message });
        } else {
          setErrors({ general: caught.message });
        }
      } else {
        setErrors({
          general: caught instanceof Error ? caught.message : "Registration failed",
        });
      }
      setSubmitting(false);
    }
  };

  const fieldError = (message?: string): React.JSX.Element | null =>
    message ? (
      <span className="mt-1 block text-xs text-[color:var(--bo-error-fg)]">{message}</span>
    ) : null;

  return (
    <div className="w-full max-w-md space-y-6 bo-auth-card">
      <div className="space-y-1 text-center">
        <p className="bo-eyebrow">
          Brasaland Backoffice
        </p>
        <h1 className="bo-title text-2xl md:text-3xl">Create account</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <label className="block text-sm bo-fg-secondary">
          Name
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
            className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
          />
          {fieldError(errors.name)}
        </label>

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
          {fieldError(errors.email)}
        </label>

        <label className="block text-sm bo-fg-secondary">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
            className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
          />
          {fieldError(errors.password)}
          <span className="mt-1 block text-xs bo-muted">
            At least 8 characters.
          </span>
        </label>

        {errors.general ? (
          <p
            role="alert"
            className="bo-alert-error rounded-md px-3 py-2 text-sm"
          >
            {errors.general}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="bo-btn-primary w-full py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
        >
          {submitting ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p className="text-center text-sm bo-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent-muted)]">
          Sign in
        </Link>
      </p>
    </div>
  );
}
