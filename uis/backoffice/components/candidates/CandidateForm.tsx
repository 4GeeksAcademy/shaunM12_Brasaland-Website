"use client";

import { FormEvent, useMemo, useState } from "react";
import { useApiState } from "@/hooks/useApiState";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/constants";
import { CandidateInput } from "@/types/api";

interface CandidateFormProps {
  mode: "create" | "edit";
  initialValue?: CandidateInput;
  onSubmit: (payload: CandidateInput) => Promise<void>;
  submitLabel: string;
}

const EMPTY_VALUE: CandidateInput = {
  full_name: "",
  email: "",
  phone: "",
  position: "Executive Assistant",
  linkedin_url: "",
  cv_url: "",
  status: "received",
  stage: "pending",
  experience_years: 0,
};

export default function CandidateForm({
  mode,
  initialValue,
  onSubmit,
  submitLabel,
}: CandidateFormProps): React.JSX.Element {
  const startValue = useMemo(() => initialValue ?? EMPTY_VALUE, [initialValue]);

  const [form, setForm] = useState<CandidateInput>(startValue);
  const { state, error, execute } = useApiState<null>(null);
  const [message, setMessage] = useState("");

  const requiredFields: Array<keyof CandidateInput> = [
    "full_name",
    "email",
    "phone",
    "position",
    "linkedin_url",
    "cv_url",
  ];

  const onInputChange = <K extends keyof CandidateInput>(
    key: K,
    value: CandidateInput[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const validate = (): string | null => {
    for (const key of requiredFields) {
      const rawValue = String(form[key] ?? "").trim();
      if (!rawValue) {
        return `Field ${key.replace("_", " ")} is required.`;
      }
    }

    if (Number.isNaN(form.experience_years) || form.experience_years < 0) {
      return "Years of experience must be 0 or greater.";
    }

    return null;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationError = validate();
    if (validationError) {
      setMessage(validationError);
      return;
    }

    setMessage("");

    try {
      await execute(
        () =>
          onSubmit({
            ...form,
            full_name: form.full_name.trim(),
            email: form.email.trim(),
            phone: form.phone.trim(),
            position: form.position.trim(),
            linkedin_url: form.linkedin_url.trim(),
            cv_url: form.cv_url.trim(),
          }),
        {
          mapResult: () => null,
        },
      );

      setMessage(
        mode === "create"
          ? "Candidate saved successfully."
          : "Candidate updated successfully.",
      );

      if (mode === "create") {
        setForm(EMPTY_VALUE);
      }
    } catch {
      // Error state is managed by useApiState.
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 shadow-2xl shadow-black/20">
      <h3 className="text-lg font-extrabold text-amber-300">
        {mode === "create" ? "Register candidate" : "Edit candidate"}
      </h3>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm text-amber-100">
          Full name
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.full_name}
            onChange={(event) => onInputChange("full_name", event.target.value)}
            placeholder="Full name"
          />
        </label>

        <label className="text-sm text-amber-100">
          Email
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            type="email"
            value={form.email}
            onChange={(event) => onInputChange("email", event.target.value)}
            placeholder="Email"
          />
        </label>

        <label className="text-sm text-amber-100">
          Phone
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.phone}
            onChange={(event) => onInputChange("phone", event.target.value)}
            placeholder="Phone"
          />
        </label>

        <label className="text-sm text-amber-100">
          Position
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.position}
            onChange={(event) => onInputChange("position", event.target.value)}
            placeholder="Position"
          />
        </label>

        <label className="text-sm text-amber-100">
          LinkedIn URL
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.linkedin_url}
            onChange={(event) => onInputChange("linkedin_url", event.target.value)}
            placeholder="LinkedIn URL"
          />
        </label>

        <label className="text-sm text-amber-100">
          CV URL
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.cv_url}
            onChange={(event) => onInputChange("cv_url", event.target.value)}
            placeholder="CV URL"
          />
        </label>

        <label className="text-sm text-amber-100">
          Status
          <select
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.status}
            onChange={(event) => onInputChange("status", event.target.value as CandidateInput["status"])}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm text-amber-100">
          Stage
          <select
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            value={form.stage}
            onChange={(event) => onInputChange("stage", event.target.value as CandidateInput["stage"])}
          >
            {STAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm text-amber-100 md:col-span-2">
          Years of experience
          <input
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/90 px-3 py-2 text-amber-100 placeholder-stone-400 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
            type="number"
            min={0}
            value={form.experience_years}
            onChange={(event) => onInputChange("experience_years", Number(event.target.value || 0))}
            placeholder="Years of experience"
          />
        </label>
      </div>

      <button
        type="submit"
        disabled={state === "loading"}
        className="rounded-md bg-amber-700 px-4 py-2 text-white transition disabled:opacity-60"
      >
        {state === "loading" ? "Saving..." : submitLabel}
      </button>

      {(message && state !== "success") && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{message}</p>
      )}
      {state === "error" && !message && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>
      )}
      {state === "success" && (
        <p className="rounded-md bg-green-50 p-2 text-sm text-green-700">{message}</p>
      )}
    </form>
  );
}
