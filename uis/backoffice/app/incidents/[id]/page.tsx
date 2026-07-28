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
    <main className="bo-page">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="bo-header">
          <Link
            href="/incidents"
            className="text-sm font-semibold text-[color:var(--bo-accent)] transition hover:text-[color:var(--bo-accent-muted)]"
          >
            ← Back to incidents
          </Link>
          <p className="mt-4 bo-eyebrow">Incident Manager</p>
          <h1 className="mt-1 bo-title">Incident Detail</h1>
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
          <section className="bo-card-lg">
            <dl className="grid gap-4 text-sm md:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">id</dt>
                <dd className="mt-1 font-semibold text-[color:var(--bo-fg)]">{incident.id}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">title</dt>
                <dd className="mt-1 font-semibold text-[color:var(--bo-fg)]">{incident.title}</dd>
              </div>
              <div className="md:col-span-2">
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">description</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{incident.description}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">category</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{toLabel(incident.category)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">status</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{toLabel(incident.status)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">origin</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{toLabel(incident.origin)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">branch</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{toLabel(incident.branch)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">created_at</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{incident.created_at}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] bo-muted">updated_at</dt>
                <dd className="mt-1 text-[color:var(--bo-fg)]">{incident.updated_at}</dd>
              </div>
            </dl>
          </section>
        ) : null}
      </div>
    </main>
  );
}
