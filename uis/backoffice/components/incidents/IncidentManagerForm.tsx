"use client";

import { FormEvent, useState } from "react";
import { createManagedIncident } from "@/lib/incidents-api";
import {
  MANAGED_BRANCHES,
  MANAGED_CATEGORIES,
  MANAGED_ORIGINS,
  ManagedIncident,
  ManagedIncidentBranch,
  ManagedIncidentCategory,
  ManagedIncidentCreate,
  ManagedIncidentOrigin,
} from "@/types/incidents";

const EMPTY: ManagedIncidentCreate = {
  title: "",
  description: "",
  category: "equipment_failure",
  origin: "branch",
  branch: "central",
};

export default function IncidentManagerForm({
  onCreated,
}: {
  onCreated: (incident: ManagedIncident) => void;
}): React.JSX.Element {
  const [form, setForm] = useState<ManagedIncidentCreate>(EMPTY);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validateClient = (): boolean => {
    const next: Record<string, string> = {};
    if (!form.title.trim()) {
      next.title = "Title is required.";
    }
    if (!form.description.trim()) {
      next.description = "Description is required.";
    }
    if (!form.category) {
      next.category = "Category is required.";
    }
    if (!form.origin) {
      next.origin = "Origin is required.";
    }
    if (!form.branch) {
      next.branch = "Branch is required.";
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);
    if (!validateClient()) {
      return;
    }

    setSubmitting(true);
    try {
      const created = await createManagedIncident({
        title: form.title.trim(),
        description: form.description.trim(),
        category: form.category,
        origin: form.origin,
        branch: form.branch,
        status: "open",
      });
      onCreated(created);
      setForm(EMPTY);
      setFieldErrors({});
    } catch (caught) {
      setFormError(
        caught instanceof Error
          ? caught.message
          : "Could not create the incident. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
      className="space-y-4 rounded-2xl border border-amber-200/15 bg-stone-950/70 p-5"
    >
      <h2 className="text-lg font-semibold text-amber-100">Report an incident</h2>
      <p className="text-sm text-stone-400">
        Required fields are validated before submit. API field errors show in plain language.
      </p>

      <label className="block text-sm">
        <span className="text-amber-200/80">Title</span>
        <input
          className="mt-1 w-full rounded-lg border border-amber-200/20 bg-stone-900 px-3 py-2"
          value={form.title}
          disabled={submitting}
          onChange={(event) =>
            setForm((current) => ({ ...current, title: event.target.value }))
          }
        />
        {fieldErrors.title ? (
          <span className="mt-1 block text-xs text-rose-300">{fieldErrors.title}</span>
        ) : null}
      </label>

      <label className="block text-sm">
        <span className="text-amber-200/80">Description</span>
        <textarea
          className="mt-1 w-full rounded-lg border border-amber-200/20 bg-stone-900 px-3 py-2"
          rows={3}
          value={form.description}
          disabled={submitting}
          onChange={(event) =>
            setForm((current) => ({ ...current, description: event.target.value }))
          }
        />
        {fieldErrors.description ? (
          <span className="mt-1 block text-xs text-rose-300">
            {fieldErrors.description}
          </span>
        ) : null}
      </label>

      <div className="grid gap-3 md:grid-cols-3">
        <label className="block text-sm">
          <span className="text-amber-200/80">Category</span>
          <select
            className="mt-1 w-full rounded-lg border border-amber-200/20 bg-stone-900 px-3 py-2"
            value={form.category}
            disabled={submitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                category: event.target.value as ManagedIncidentCategory,
              }))
            }
          >
            {MANAGED_CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-amber-200/80">Origin</span>
          <select
            className="mt-1 w-full rounded-lg border border-amber-200/20 bg-stone-900 px-3 py-2"
            value={form.origin}
            disabled={submitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                origin: event.target.value as ManagedIncidentOrigin,
              }))
            }
          >
            {MANAGED_ORIGINS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-amber-200/80">Branch</span>
          <select
            className="mt-1 w-full rounded-lg border border-amber-200/20 bg-stone-900 px-3 py-2"
            value={form.branch}
            disabled={submitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                branch: event.target.value as ManagedIncidentBranch,
              }))
            }
          >
            {MANAGED_BRANCHES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

      {formError ? <p className="text-sm text-rose-300">{formError}</p> : null}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-full border border-amber-300 bg-amber-300/20 px-5 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-amber-100 transition hover:bg-amber-300/30 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Saving…" : "Create incident"}
      </button>
    </form>
  );
}
