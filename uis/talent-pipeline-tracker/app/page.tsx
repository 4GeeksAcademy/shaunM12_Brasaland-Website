"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CandidateCard from "@/components/candidates/CandidateCard";
import CandidateForm from "@/components/candidates/CandidateForm";
import { useApiState } from "@/hooks/useApiState";
import { createRecord, getRecords } from "@/lib/api";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/constants";
import { Candidate, CandidateInput } from "@/types/api";

export default function Home() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const {
    state: fetchState,
    data: records,
    error: fetchError,
    execute: runFetch,
  } = useApiState<Candidate[]>([]);

  const status = searchParams.get("status") ?? "";
  const stage = searchParams.get("stage") ?? "";
  const search = searchParams.get("search") ?? "";
  const recordsList = records ?? [];

  const setParam = useCallback(
    (key: "status" | "stage" | "search", value: string) => {
      const next = new URLSearchParams(searchParams.toString());

      if (value.trim()) {
        next.set(key, value.trim());
      } else {
        next.delete(key);
      }

      router.replace(`/?${next.toString()}`);
    },
    [router, searchParams]
  );

  const clearFilters = useCallback(() => {
    router.replace("/");
  }, [router]);

  const fetchCandidates = useCallback(async () => {
    try {
      await runFetch(() =>
        getRecords({
          status: status || undefined,
          stage: stage || undefined,
          search: search || undefined,
        }),
      );
    } catch {
      // Error state is managed by the hook.
    }
  }, [runFetch, stage, status, search]);

  useEffect(() => {
    void fetchCandidates();
  }, [fetchCandidates]);

  const visibleRecords = useMemo(() => {
    if (!search) return recordsList;
    const needle = search.toLowerCase();
    return recordsList.filter(
      (candidate) =>
        candidate.full_name.toLowerCase().includes(needle) ||
        candidate.email.toLowerCase().includes(needle),
    );
  }, [recordsList, search]);

  const onCreateCandidate = async (payload: CandidateInput) => {
    await createRecord(payload);
    await fetchCandidates();
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/10 bg-stone-950/95 p-6 text-amber-300 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-wider">Brasaland Digital</p>
          <h1 className="mt-1 text-2xl font-extrabold md:text-3xl">
            Executive Assistant Talent Pipeline
          </h1>
          <p className="mt-2 text-sm text-amber-100">
            Candidate operations for People Team and Brasaland leadership.
          </p>
        </header>

        <section className="grid gap-4 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 md:grid-cols-3">
          <label className="text-sm text-stone-100">
            Filter by status
            <select
              value={status}
              onChange={(event) => setParam("status", event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20 outline-none transition"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-stone-100">
            Filter by stage
            <select
              value={stage}
              onChange={(event) => setParam("stage", event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20 outline-none transition"
            >
              <option value="">All stages</option>
              {STAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-stone-100">
            Search by name or email
            <input
              value={search}
              onChange={(event) => setParam("search", event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20 outline-none transition"
              placeholder="example: ashley or ashley@email.com"
            />
          </label>

        </section>

        <div className="flex justify-end">
          <button
            onClick={clearFilters}
            className="mt-2 rounded-full border border-amber-300 px-4 py-1 text-sm font-semibold text-amber-300 hover:bg-amber-300/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300 transition"
          >
            Show All / Clear Filters
          </button>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-extrabold text-amber-300">Candidate list</h2>
          {fetchState === "loading" && (
            <p className="rounded-md bg-stone-950/80 p-3 text-sm text-stone-100">Loading candidates...</p>
          )}
          {fetchState === "error" && (
            <p className="rounded-md bg-red-300/10 p-3 text-sm text-red-300">{fetchError}</p>
          )}
          {fetchState === "success" && visibleRecords.length === 0 && (
            <p className="rounded-md bg-stone-950/80 p-3 text-sm text-stone-100">No candidates found.</p>
          )}
          {fetchState === "success" && visibleRecords.length > 0 && (
            <ul className="space-y-3">
              {visibleRecords.map((candidate) => (
                <CandidateCard key={candidate.id} candidate={candidate} />
              ))}
            </ul>
          )}
        </section>

        <CandidateForm
          mode="create"
          submitLabel="Register candidate"
          onSubmit={onCreateCandidate}
        />
      </div>
    </main>
  );
}
