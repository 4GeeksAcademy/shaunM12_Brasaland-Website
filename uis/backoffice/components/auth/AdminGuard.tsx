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
      <div className="bo-danger-panel mx-auto max-w-md space-y-3 rounded-xl p-6 text-center">
        <h2 className="text-lg font-semibold">Admins only</h2>
        <p className="text-sm text-[color:var(--bo-error-fg)]/80">
          You do not have permission to view this page.
        </p>
        <Link
          href="/account/profile"
          className="bo-btn-secondary inline-block border-[color:var(--bo-error-border)] text-[color:var(--bo-error-fg)]"
        >
          Back to profile
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
