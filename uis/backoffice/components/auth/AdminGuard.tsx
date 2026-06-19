"use client";

import Link from "next/link";

import { useAuth } from "@/context/AuthProvider";

/**
 * Gate admin-only views. Assumes it is rendered inside an authenticated area
 * (e.g. under AuthGuard); the API also enforces admin on these endpoints.
 */
export default function AdminGuard({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const { user } = useAuth();

  if (!user?.is_admin) {
    return (
      <div className="mx-auto max-w-md space-y-3 rounded-xl border border-rose-500/40 bg-rose-950/30 p-6 text-center text-rose-100">
        <h2 className="text-lg font-semibold">Admins only</h2>
        <p className="text-sm text-rose-200/80">
          You do not have permission to view this page.
        </p>
        <Link
          href="/account/profile"
          className="inline-block rounded-full border border-rose-300/60 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] transition hover:bg-rose-300/10"
        >
          Back to profile
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
