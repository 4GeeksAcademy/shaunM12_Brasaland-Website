"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CandidateCard from "@/components/candidates/CandidateCard";
import CandidateForm from "@/components/candidates/CandidateForm";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
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
    <main className="bo-page">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="bo-header text-[color:var(--bo-accent)] shadow-2xl shadow-[color:var(--bo-shadow)]">
          <p className="text-sm uppercase tracking-wider">Brasaland Digital</p>
          <h1 className="mt-1 text-2xl font-extrabold md:text-3xl">
            Executive Assistant Talent Pipeline
          </h1>
          <p className="mt-2 text-sm text-[color:var(--bo-heading)]">
            Milestone 3 tracker UI powered by milestone 2 shared business logic.
          </p>
        </header>

        <section className="grid gap-4 bo-card-lg md:grid-cols-3">
          <label className="text-sm text-[color:var(--bo-fg)]">
            Filter by status
            <select
              value={status}
              onChange={(event) => setParam("status", event.target.value)}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
            Filter by stage
            <select
              value={stage}
              onChange={(event) => setParam("stage", event.target.value)}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
            >
              <option value="">All stages</option>
              {STAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
            Search
            <input
              value={search}
              onChange={(event) => setParam("search", event.target.value)}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
              placeholder="Search by name, phone, email, or position"
            />
          </label>
        </section>

        <div className="flex justify-end">
          <button
            onClick={clearFilters}
            className="bo-btn-secondary mt-2 text-sm normal-case tracking-normal"
          >
            Show All / Clear Filters
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="bo-stat-success">
            <p className="text-xs uppercase tracking-[0.14em] text-[color:var(--bo-success-fg)]">Total registrations</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-success)]">{insights.totalRegistrations}</p>
          </article>

          <article className="bo-stat-info">
            <p className="bo-info-label text-xs uppercase tracking-[0.14em]">Tracked locations</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">{insights.totalLocations}</p>
          </article>

          <article className="bo-stat-accent">
            <p className="text-xs uppercase tracking-[0.14em] text-[color:var(--bo-accent-muted)]">Colombia opt-in</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">{insights.colombiaOptInCount}</p>
          </article>
        </section>

        <section className="space-y-3">
          <h2 className="bo-subtitle text-[color:var(--bo-accent)]">Candidate list</h2>

          {fetchState === "loading" && <LoadingState label="Loading candidates..." />}

          {fetchState === "error" && (
            <ErrorState
              message={fetchError || "We couldn't load the candidate list."}
              onRetry={() => void fetchCandidates()}
              showHomeLink={false}
            />
          )}

          {fetchState === "success" && visibleRecords.length === 0 && (
            <p className="rounded-md bg-[color:var(--bo-input-bg)] p-3 text-sm text-[color:var(--bo-fg)]">No candidates found.</p>
          )}

          {fetchState === "success" && visibleRecords.length > 0 && (
            <>
              <ul className="space-y-3">
                {paginatedRecords.map((candidate) => (
                  <CandidateCard key={candidate.id} candidate={candidate} />
                ))}
              </ul>

              <div className="mt-3 flex flex-col gap-2 rounded-lg border border-[color:var(--bo-input-border)] bg-[color:var(--bo-panel)] p-3 text-sm bo-muted md:flex-row md:items-center md:justify-between">
                <p>
                  Showing {pageStart}-{pageEnd} of {visibleRecords.length} candidates
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    disabled={currentPage === 1}
                    className="rounded-md border border-[color:var(--bo-input-border)] px-3 py-1 text-[color:var(--bo-fg)] transition hover:bg-[color:var(--bo-accent-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-xs uppercase tracking-[0.12em] bo-muted">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                    disabled={currentPage === totalPages}
                    className="rounded-md border border-[color:var(--bo-input-border)] px-3 py-1 text-[color:var(--bo-fg)] transition hover:bg-[color:var(--bo-accent-soft)] disabled:cursor-not-allowed disabled:opacity-50"
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
