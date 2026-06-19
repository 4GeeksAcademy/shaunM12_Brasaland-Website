"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/context/AuthProvider";
import { LOGIN_PATH } from "@/lib/auth-config";

function FullScreenMessage({ text }: { text: string }): React.JSX.Element {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-950 text-sm text-stone-300">
      {text}
    </div>
  );
}

/**
 * Client-side gate: ensures an authenticated session before rendering children.
 * Backs up the server middleware and handles the access-token-expired case
 * (when the cookie exists but the token can no longer be refreshed).
 */
export default function AuthGuard({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = encodeURIComponent(pathname ?? "/");
      router.replace(`${LOGIN_PATH}?next=${next}`);
    }
  }, [status, router, pathname]);

  if (status === "loading") {
    return <FullScreenMessage text="Loading your session..." />;
  }

  if (status === "unauthenticated") {
    return <FullScreenMessage text="Redirecting to sign in..." />;
  }

  return <>{children}</>;
}
