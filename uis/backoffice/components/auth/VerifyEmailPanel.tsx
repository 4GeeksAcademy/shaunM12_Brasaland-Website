"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { verifyEmail } from "@/lib/auth-api";

type Status = "verifying" | "success" | "error" | "missing";

export default function VerifyEmailPanel(): React.JSX.Element {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<Status>(token ? "verifying" : "missing");
  const [message, setMessage] = useState("");
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) {
      return;
    }
    attempted.current = true;
    void (async () => {
      try {
        await verifyEmail(token);
        setStatus("success");
      } catch (caught) {
        setStatus("error");
        setMessage(
          caught instanceof Error ? caught.message : "Verification failed",
        );
      }
    })();
  }, [token]);

  return (
    <div className="w-full max-w-md space-y-5 rounded-2xl border border-[color:var(--bo-panel-border)] bg-stone-950/95 p-8 text-center shadow-2xl shadow-black/30">
      <h1 className="bo-title text-2xl md:text-3xl">Email verification</h1>

      {status === "verifying" ? (
        <p className="text-sm bo-muted">Verifying your email...</p>
      ) : null}

      {status === "missing" ? (
        <p className="text-sm text-[color:var(--bo-error-fg)]">No verification token provided.</p>
      ) : null}

      {status === "error" ? (
        <p className="text-sm text-[color:var(--bo-error-fg)]">{message}</p>
      ) : null}

      {status === "success" ? (
        <p className="text-sm text-emerald-200">
          Your email has been verified. Thank you!
        </p>
      ) : null}

      <Link
        href="/"
        className="inline-block rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--bo-accent-muted)] transition hover:bg-[color:var(--bo-accent-soft)]"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
