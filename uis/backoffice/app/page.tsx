"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CandidateCard from "@/components/candidates/CandidateCard";
import CandidateForm from "@/components/candidates/CandidateForm";
import { useApiState } from "@/hooks/useApiState";
import { createRecord, getRecords } from "@/lib/api";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/constants";
import { Candidate, CandidateInput } from "@/types/api";

const ITEMS_PER_PAGE = 10;

function readTextValue(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  return "";
}

function readBooleanValue(record: Record<string, unknown>, keys: string[]): boolean {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "boolean") {
      return value;
    }

    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (normalized === "true" || normalized === "yes" || normalized === "1") {
        return true;
      }

      if (normalized === "false" || normalized === "no" || normalized === "0") {
        return false;
      }
    }
  }

  return false;
}

export default function Page(): React.JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [currentPage, setCurrentPage] = useState(1);

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

  const insights = useMemo(() => {
    const uniqueLocations = new Set<string>();
    let colombiaOptInCount = 0;

    for (const candidate of recordsList) {
      const record = candidate as unknown as Record<string, unknown>;

      const country = readTextValue(record, ["country", "country_name"]).toLowerCase();
      const city = readTextValue(record, ["city", "city_name"]);
      const favoriteLocation = readTextValue(record, [
        "favorite_brasaland_location",
        "favorite_location",
        "favoriteLocation",
        "location",
      ]);

      const locationKey = favoriteLocation || [country, city].filter(Boolean).join("|");
      if (locationKey) {
        uniqueLocations.add(locationKey.toLowerCase());
      }

      const wantsEmailOffers = readBooleanValue(record, [
        "wants_email_offers",
        "wantsEmailOffers",
        "email_offers_opt_in",
      ]);

      if (country === "colombia" && wantsEmailOffers) {
        colombiaOptInCount += 1;
      }
    }

    return {
      totalRegistrations: recordsList.length,
      totalLocations: uniqueLocations.size,
      colombiaOptInCount,
    };
  }, [recordsList]);

  const setParam = useCallback(
    (key: "status" | "stage" | "search", value: string) => {
      const next = new URLSearchParams(searchParams.toString());

      if (value.trim()) {
        next.set(key, value.trim());
      } else {
        next.delete(key);
      }

      const query = next.toString();
      router.replace(query ? `/?${query}` : "/");
    },
    [router, searchParams],
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
    if (!search) {
      return recordsList;
    }

    const needle = search.toLowerCase();

    return recordsList.filter((candidate) =>
      [candidate.full_name, candidate.phone, candidate.email, candidate.position]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [recordsList, search]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(visibleRecords.length / ITEMS_PER_PAGE)),
    [visibleRecords.length],
  );

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, totalPages));
  }, [totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [status, stage, search]);

  const paginatedRecords = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return visibleRecords.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [currentPage, visibleRecords]);

  const pageStart = visibleRecords.length === 0 ? 0 : (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const pageEnd = Math.min(currentPage * ITEMS_PER_PAGE, visibleRecords.length);

  const onCreateCandidate = async (payload: CandidateInput): Promise<void> => {
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
            Milestone 3 tracker UI powered by milestone 2 shared business logic.
          </p>
        </header>

        <section className="grid gap-4 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 md:grid-cols-3">
          <label className="text-sm text-stone-100">
            Filter by status
            <select
              value={status}
              onChange={(event) => setParam("status", event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
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
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
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
            Search
            <input
              value={search}
              onChange={(event) => setParam("search", event.target.value)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
              placeholder="Search by name, phone, email, or position"
            />
          </label>
        </section>

        <div className="flex justify-end">
          <button
            onClick={clearFilters}
            className="mt-2 rounded-full border border-amber-300 px-4 py-1 text-sm font-semibold text-amber-300 transition hover:bg-amber-300/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300"
          >
            Show All / Clear Filters
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-emerald-500/30 bg-emerald-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.14em] text-emerald-200">Total registrations</p>
            <p className="mt-1 text-3xl font-extrabold text-emerald-100">{insights.totalRegistrations}</p>
          </article>

          <article className="rounded-xl border border-cyan-500/30 bg-cyan-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.14em] text-cyan-200">Tracked locations</p>
            <p className="mt-1 text-3xl font-extrabold text-cyan-100">{insights.totalLocations}</p>
          </article>

          <article className="rounded-xl border border-amber-500/30 bg-amber-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.14em] text-amber-200">Colombia opt-in</p>
            <p className="mt-1 text-3xl font-extrabold text-amber-100">{insights.colombiaOptInCount}</p>
          </article>
        </section>

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
            <>
              <ul className="space-y-3">
                {paginatedRecords.map((candidate) => (
                  <CandidateCard key={candidate.id} candidate={candidate} />
                ))}
              </ul>

              <div className="mt-3 flex flex-col gap-2 rounded-lg border border-stone-700 bg-stone-950/70 p-3 text-sm text-stone-300 md:flex-row md:items-center md:justify-between">
                <p>
                  Showing {pageStart}-{pageEnd} of {visibleRecords.length} candidates
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    disabled={currentPage === 1}
                    className="rounded-md border border-stone-600 px-3 py-1 text-stone-100 transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-xs uppercase tracking-[0.12em] text-stone-400">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                    disabled={currentPage === totalPages}
                    className="rounded-md border border-stone-600 px-3 py-1 text-stone-100 transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
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
