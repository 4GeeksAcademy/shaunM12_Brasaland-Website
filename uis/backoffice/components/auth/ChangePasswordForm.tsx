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
    "mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]";

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 bo-header"
      noValidate
    >
      <div className="space-y-1">
        <h2 className="text-lg font-bold text-[color:var(--bo-accent-muted)]">Change password</h2>
        <p className="text-sm bo-muted">Choose a new password for your account.</p>
      </div>

      <label className="block text-sm bo-fg-secondary">
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

      <label className="block text-sm bo-fg-secondary">
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

      {status === "saved" ? (
        <p className="bo-alert-success">
          Password updated.
        </p>
      ) : null}
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
        disabled={status === "saving"}
        className="rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-[color:var(--bo-heading)] transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {status === "saving" ? "Updating..." : "Update password"}
      </button>
    </form>
  );
}
