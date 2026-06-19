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
    <div className="w-full max-w-md space-y-5 rounded-2xl border border-amber-200/15 bg-stone-950/95 p-8 text-center shadow-2xl shadow-black/30">
      <h1 className="text-2xl font-extrabold text-amber-100">Email verification</h1>

      {status === "verifying" ? (
        <p className="text-sm text-stone-300">Verifying your email...</p>
      ) : null}

      {status === "missing" ? (
        <p className="text-sm text-rose-200">No verification token provided.</p>
      ) : null}

      {status === "error" ? (
        <p className="text-sm text-rose-200">{message}</p>
      ) : null}

      {status === "success" ? (
        <p className="text-sm text-emerald-200">
          Your email has been verified. Thank you!
        </p>
      ) : null}

      <Link
        href="/"
        className="inline-block rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
