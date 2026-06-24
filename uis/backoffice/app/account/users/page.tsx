"use client";

import { useCallback, useEffect, useState } from "react";

import AdminGuard from "@/components/auth/AdminGuard";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { useAuth } from "@/context/AuthProvider";
import { deleteUser, listUsers, updateUser } from "@/lib/users-api";
import { AuthUser } from "@/types/auth";

function UsersTable(): React.JSX.Element {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await listUsers());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const patch = async (
    target: AuthUser,
    changes: { is_admin?: boolean; is_active?: boolean },
  ): Promise<void> => {
    setBusyId(target.id);
    setError(null);
    try {
      await updateUser(target.id, changes);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (target: AuthUser): Promise<void> => {
    if (
      !window.confirm(`Delete user ${target.email}? This cannot be undone.`)
    ) {
      return;
    }
    setBusyId(target.id);
    setError(null);
    try {
      await deleteUser(target.id);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} showHomeLink={false} />
      ) : null}

      {loading ? (
        <LoadingState label="Loading users..." />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-amber-200/15 bg-stone-950/95">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-stone-700 text-xs uppercase tracking-[0.12em] text-stone-400">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Verified</th>
                <th className="px-4 py-3">Admin</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((row) => {
                const isSelf = row.id === currentUser?.id;
                const disabled = busyId === row.id;
                return (
                  <tr key={row.id} className="border-b border-stone-800/60">
                    <td className="px-4 py-3 text-stone-100">{row.email}</td>
                    <td className="px-4 py-3 text-stone-300">{row.name ?? "—"}</td>
                    <td className="px-4 py-3">
                      {row.is_verified ? "Yes" : "No"}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={disabled || isSelf}
                        onClick={() => patch(row, { is_admin: !row.is_admin })}
                        className="rounded-full border border-stone-600 px-3 py-1 text-xs transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {row.is_admin ? "Admin" : "Member"}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={disabled || isSelf}
                        onClick={() => patch(row, { is_active: !row.is_active })}
                        className="rounded-full border border-stone-600 px-3 py-1 text-xs transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {row.is_active ? "Active" : "Disabled"}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        disabled={disabled || isSelf}
                        onClick={() => remove(row)}
                        className="rounded-full border border-rose-400/50 px-3 py-1 text-xs font-semibold text-rose-200 transition hover:bg-rose-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function UsersAdminPage(): React.JSX.Element {
  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10 text-stone-100">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-extrabold text-amber-100">User management</h1>
          <p className="text-sm text-stone-400">
            Admin-only. Manage roles, access, and accounts.
          </p>
        </header>
        <AdminGuard>
          <UsersTable />
        </AdminGuard>
      </div>
    </main>
  );
}
