"use client";

import { useState } from "react";

import { useAuth } from "@/context/AuthProvider";
import { resendVerification } from "@/lib/auth-api";

export default function EmailVerificationBanner(): React.JSX.Element | null {
  const { user } = useAuth();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">(
    "idle",
  );
  const [message, setMessage] = useState<string>("");

  if (!user || user.is_verified) {
    return null;
  }

  const handleResend = async (): Promise<void> => {
    setState("sending");
    setMessage("");
    try {
      await resendVerification();
      setState("sent");
      setMessage("Verification email sent. Check the API console in dev.");
    } catch (caught) {
      setState("error");
      setMessage(caught instanceof Error ? caught.message : "Could not send email");
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
      <span>
        Your email is not verified.{" "}
        {message ? <span className="text-amber-200">{message}</span> : null}
      </span>
      <button
        type="button"
        onClick={handleResend}
        disabled={state === "sending"}
        className="rounded-full border border-amber-300/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {state === "sending" ? "Sending..." : "Resend verification"}
      </button>
    </div>
  );
}
