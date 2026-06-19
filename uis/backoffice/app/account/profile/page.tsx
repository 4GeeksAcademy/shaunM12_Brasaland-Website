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
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10 text-stone-100">
      <div className="mx-auto max-w-xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-extrabold text-amber-100">Your profile</h1>
          <p className="text-sm text-stone-400">Manage your account details.</p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20"
        >
          <label className="block text-sm text-stone-200">
            Email
            <input
              type="email"
              value={user?.email ?? ""}
              readOnly
              disabled
              className="mt-1 w-full cursor-not-allowed rounded-xl border border-stone-700 bg-stone-900/60 px-3 py-2 text-stone-400"
            />
          </label>

          <label className="block text-sm text-stone-200">
            Name
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            />
          </label>

          {status === "saved" ? (
            <p className="rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
              Profile saved.
            </p>
          ) : null}
          {status === "error" && error ? (
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
            {status === "saving" ? "Saving..." : "Save changes"}
          </button>
        </form>

        <ChangePasswordForm />
      </div>
    </main>
  );
}
