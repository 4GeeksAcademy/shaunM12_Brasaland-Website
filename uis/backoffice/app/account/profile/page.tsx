"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/context/AuthProvider";
import { updateUser } from "@/lib/users-api";
import ChangePasswordForm from "@/components/auth/ChangePasswordForm";

export default function ProfilePage(): React.JSX.Element {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setName(user?.name ?? "");
  }, [user?.name]);

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    if (!user) {
      return;
    }
    setStatus("saving");
    setError(null);
    try {
      await updateUser(user.id, { name });
      await refreshUser();
      setStatus("saved");
    } catch (caught) {
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "Could not save profile");
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10 text-[color:var(--bo-fg)]">
      <div className="mx-auto max-w-xl space-y-6">
        <header className="space-y-1">
          <h1 className="bo-title text-2xl md:text-3xl">Your profile</h1>
          <p className="text-sm bo-muted">Manage your account details.</p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 bo-header"
        >
          <label className="block text-sm bo-fg-secondary">
            Email
            <input
              type="email"
              value={user?.email ?? ""}
              readOnly
              disabled
              className="mt-1 w-full cursor-not-allowed rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-card)]/60 px-3 py-2 bo-muted"
            />
          </label>

          <label className="block text-sm bo-fg-secondary">
            Name
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
            />
          </label>

          {status === "saved" ? (
            <p className="bo-alert-success">
              Profile saved.
            </p>
          ) : null}
          {status === "error" && error ? (
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
            {status === "saving" ? "Saving..." : "Save changes"}
          </button>
        </form>

        <ChangePasswordForm />
      </div>
    </main>
  );
}
