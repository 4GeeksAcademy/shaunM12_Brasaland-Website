"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { getManagerIncidentById } from "@/lib/incidents-manager-api";
import { IncidentManagerRecord } from "@/types/incidents-manager";

function toLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export default function IncidentDetailPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const incidentId = Number(params.id);

  const [incident, setIncident] = useState<IncidentManagerRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadIncident = useCallback(async () => {
    if (!Number.isFinite(incidentId) || incidentId <= 0) {
      setError("Invalid incident id.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const detail = await getManagerIncidentById(incidentId);
      setIncident(detail);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load incident detail.");
      setIncident(null);
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    void loadIncident();
  }, [loadIncident]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <Link
            href="/incidents"
            className="text-sm font-semibold text-amber-300 transition hover:text-amber-200"
          >
            ← Back to incidents
          </Link>
          <p className="mt-4 text-sm uppercase tracking-[0.12em] text-amber-300">Incident Manager</p>
          <h1 className="mt-1 text-2xl font-extrabold text-amber-100 md:text-3xl">Incident Detail</h1>
        </header>

        {loading ? <LoadingState label="Loading incident detail..." /> : null}

        {error ? (
          <ErrorState
            message={error}
            onRetry={() => void loadIncident()}
            showHomeLink={false}
          />
        ) : null}

        {incident ? (
          <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
            <dl className="grid gap-4 text-sm md:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">id</dt>
                <dd className="mt-1 font-semibold text-stone-100">{incident.id}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">title</dt>
                <dd className="mt-1 font-semibold text-stone-100">{incident.title}</dd>
              </div>
              <div className="md:col-span-2">
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">description</dt>
                <dd className="mt-1 text-stone-100">{incident.description}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">category</dt>
                <dd className="mt-1 text-stone-100">{toLabel(incident.category)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">status</dt>
                <dd className="mt-1 text-stone-100">{toLabel(incident.status)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">origin</dt>
                <dd className="mt-1 text-stone-100">{toLabel(incident.origin)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">branch</dt>
                <dd className="mt-1 text-stone-100">{toLabel(incident.branch)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">created_at</dt>
                <dd className="mt-1 text-stone-100">{incident.created_at}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-stone-400">updated_at</dt>
                <dd className="mt-1 text-stone-100">{incident.updated_at}</dd>
              </div>
            </dl>
          </section>
        ) : null}
      </div>
    </main>
  );
}
