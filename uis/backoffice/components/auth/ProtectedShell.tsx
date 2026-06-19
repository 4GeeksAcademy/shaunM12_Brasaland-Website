"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/context/AuthProvider";
import { isPublicPath, LOGIN_PATH } from "@/lib/auth-config";
import BackofficeTabs from "@/components/backoffice-tabs";
import AuthGuard from "./AuthGuard";
import EmailVerificationBanner from "./EmailVerificationBanner";

function SessionBar(): React.JSX.Element {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async (): Promise<void> => {
    await logout();
    router.replace(LOGIN_PATH);
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-200/10 bg-stone-950 px-4 py-2 text-xs text-stone-300">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/" className="font-semibold text-amber-300">
          Brasaland Backoffice
        </Link>
        <Link href="/account/profile" className="transition hover:text-amber-200">
          Profile
        </Link>
        {user?.is_admin ? (
          <Link href="/account/users" className="transition hover:text-amber-200">
            Users
          </Link>
        ) : null}
      </div>
      <div className="flex items-center gap-3">
        {user ? <span className="text-stone-400">{user.email}</span> : null}
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-full border border-amber-300/70 px-3 py-1 font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
        >
          Log out
        </button>
      </div>
    </div>
  );
}

/**
 * Wraps the whole app. Public auth pages render bare; every other route is
 * gated by AuthGuard and gets the session bar + email-verification banner.
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
      <div className="border-b border-amber-200/10 bg-stone-950 px-4 py-2">
        <BackofficeTabs />
      </div>
      <EmailVerificationBanner />
      {children}
    </AuthGuard>
  );
}
