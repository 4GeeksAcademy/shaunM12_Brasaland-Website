"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthProvider";
import { AuthApiError, login as verifyCredentials } from "@/lib/auth-api";
import { updateUser } from "@/lib/users-api";

const MIN_PASSWORD_LENGTH = 8;

export default function ChangePasswordForm(): React.JSX.Element {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setError(null);

    if (!user) {
      return;
    }
    if (next.length < MIN_PASSWORD_LENGTH) {
      setError(`New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (next !== confirm) {
      setError("New password and confirmation do not match.");
      return;
    }

    setStatus("saving");
    try {
      // Confirm the current password before changing it.
      await verifyCredentials(user.email, current);
    } catch (caught) {
      setStatus("idle");
      if (caught instanceof AuthApiError && caught.status === 401) {
        setError("Current password is incorrect.");
      } else {
        setError(caught instanceof Error ? caught.message : "Verification failed");
      }
      return;
    }

    try {
      await updateUser(user.id, { password: next });
      setStatus("saved");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (caught) {
      setStatus("idle");
      setError(caught instanceof Error ? caught.message : "Could not update password");
    }
  };

  const inputClass =
    "mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20";

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20"
      noValidate
    >
      <div className="space-y-1">
        <h2 className="text-lg font-bold text-amber-200">Change password</h2>
        <p className="text-sm text-stone-400">Choose a new password for your account.</p>
      </div>

      <label className="block text-sm text-stone-200">
        Current password
        <input
          type="password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          required
          autoComplete="current-password"
          className={inputClass}
        />
      </label>

      <label className="block text-sm text-stone-200">
        New password
        <input
          type="password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
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

      {status === "saved" ? (
        <p className="rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          Password updated.
        </p>
      ) : null}
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
        disabled={status === "saving"}
        className="rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {status === "saving" ? "Updating..." : "Update password"}
      </button>
    </form>
  );
}
