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
      <span className="mt-1 block text-xs text-rose-300">{message}</span>
    ) : null;

  return (
    <div className="w-full max-w-md space-y-6 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 shadow-2xl shadow-black/30">
      <div className="space-y-1 text-center">
        <p className="text-sm uppercase tracking-[0.16em] text-amber-300">
          Brasaland Backoffice
        </p>
        <h1 className="text-2xl font-extrabold text-amber-100">Create account</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <label className="block text-sm text-stone-200">
          Name
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
          />
          {fieldError(errors.name)}
        </label>

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
          {fieldError(errors.email)}
        </label>

        <label className="block text-sm text-stone-200">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
          />
          {fieldError(errors.password)}
          <span className="mt-1 block text-xs text-stone-500">
            At least 8 characters.
          </span>
        </label>

        {errors.general ? (
          <p
            role="alert"
            className="rounded-md bg-rose-500/10 px-3 py-2 text-sm text-rose-200"
          >
            {errors.general}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p className="text-center text-sm text-stone-400">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-amber-300 hover:text-amber-200">
          Sign in
        </Link>
      </p>
    </div>
  );
}
