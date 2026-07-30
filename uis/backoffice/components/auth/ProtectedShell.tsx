"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/context/AuthProvider";
import { isPublicPath, LOGIN_PATH } from "@/lib/auth-config";
import BackofficeTabs from "@/components/backoffice-tabs";
import ThemeToggle from "@/components/theme-toggle";
import AuthGuard from "./AuthGuard";

function SessionBar(): React.JSX.Element {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async (): Promise<void> => {
    await logout();
    router.replace(LOGIN_PATH);
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--bo-panel-border)] bg-[color:var(--bo-shell-bg)] px-4 py-2 text-xs text-[color:var(--bo-shell-fg)]">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/" className="font-semibold text-[color:var(--bo-accent)]">
          Brasaland Backoffice
        </Link>
        <Link
          href="/account/profile"
          className="transition hover:text-[color:var(--bo-blue)]"
        >
          Profile
        </Link>
        {user?.is_admin ? (
          <Link
            href="/account/users"
            className="transition hover:text-[color:var(--bo-blue)]"
          >
            Users
          </Link>
        ) : null}
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        {user ? (
          <span className="text-[color:var(--bo-muted)]">{user.email}</span>
        ) : null}
        <button
          type="button"
          onClick={handleLogout}
          className="bo-btn-secondary normal-case tracking-normal"
        >
          Log out
        </button>
      </div>
    </div>
  );
}

/**
 * Wraps the whole app. Public auth pages render bare; every other route is
 * gated by AuthGuard and gets the session bar + navigation tabs.
 */
export default function ProtectedShell({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const pathname = usePathname();

  if (pathname && isPublicPath(pathname)) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      <SessionBar />
      <div className="bo-nav-shell border-b border-[color:var(--bo-panel-border)] bg-[color:var(--bo-shell-bg)] px-4 py-3">
        <BackofficeTabs />
      </div>
      {children}
    </AuthGuard>
  );
}
