import Link from "next/link";
import { DataList } from "@/components/data-list";
import {
  buildRegistrationDashboard,
  REGISTRATION_COUNTRY_OPTIONS,
} from "@/lib/registration-analytics";

export default async function RegistrationAnalyticsPage({
  searchParams,
}: {
  searchParams?: Promise<{ country?: string; referenceDate?: string }>;
}): Promise<React.JSX.Element> {
  const resolvedSearchParams = await searchParams;
  const dashboard = await buildRegistrationDashboard({
    country: resolvedSearchParams?.country,
    referenceDate: resolvedSearchParams?.referenceDate,
  });

  return (
    <main className="bo-page">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">Brasa Points Registration Analytics</p>
          <h1 className="mt-2 bo-title">
            Registration Aggregated Reports
          </h1>
          <p className="mt-2 max-w-3xl text-sm bo-muted">
            Brasa Points loyalty signup analytics. Sourced from registration data only, kept separate
            from operations reporting.
          </p>
        </header>

        <section className="bo-card">
          <form className="grid gap-4 md:grid-cols-3" method="get">
            <label className="text-sm text-[color:var(--bo-fg)]">
              Country scope
              <select
                name="country"
                defaultValue={dashboard.countryFilter}
                className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
              >
                {REGISTRATION_COUNTRY_OPTIONS.map((option) => (
                  <option key={option} value={option === "All" ? "" : option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm text-[color:var(--bo-fg)]">
              Reference date
              <input
                type="date"
                name="referenceDate"
                defaultValue={dashboard.referenceDate}
                className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
              />
            </label>

            <div className="flex items-end gap-2">
              <button
                type="submit"
                className="bo-btn-primary w-full rounded-xl px-3 py-2 text-sm normal-case tracking-normal"
              >
                Refresh reports
              </button>
              <Link
                href="/registration-analytics"
                className="rounded-xl border border-[color:var(--bo-input-border)] px-3 py-2 text-sm bo-fg-secondary transition hover:bg-[color:var(--bo-accent-soft)]"
              >
                Reset
              </Link>
            </div>
          </form>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="bo-stat-success">
            <p className="text-xs uppercase tracking-[0.12em] text-[color:var(--bo-success-fg)]">Total registrations</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-success)]">{dashboard.totalRegistrations}</p>
          </article>

          <article className="bo-stat-accent">
            <p className="text-xs uppercase tracking-[0.12em] text-[color:var(--bo-accent-muted)]">Email opt-in rate</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">{dashboard.emailOptInRate}%</p>
            <p className="text-xs text-[color:var(--bo-accent-muted)]/80">{dashboard.emailOptInCount} registrations opted in</p>
          </article>

          <article className="bo-stat-info">
            <p className="bo-info-label text-xs uppercase tracking-[0.12em]">Average age</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">{dashboard.ageAverage}</p>
            <p className="text-xs text-[color:var(--bo-muted)]">
              Min {dashboard.ageMinimum} / Max {dashboard.ageMaximum}
            </p>
          </article>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <DataList title="Registrations by country" rows={dashboard.registrationsByCountry} />
          <DataList title="Registrations by city" rows={dashboard.registrationsByCity} />
          <DataList title="Discovery channels" rows={dashboard.registrationsByDiscoveryChannel} />
          <DataList title="Dietary preference selections" rows={dashboard.dietaryPreferenceSelections} />
        </section>

        <section className="rounded-2xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-panel)] p-5">
          <h2 className="text-lg font-bold text-[color:var(--bo-accent-muted)]">City registration summary</h2>
          <p className="mt-1 text-sm bo-muted">
            Numeric summary generated with shared utility functions for deterministic reporting.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {dashboard.cityRegistrationSummary.map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-[color:var(--bo-input-border)]/80 bg-[color:var(--bo-card)] p-3"
              >
                <p className="text-xs uppercase tracking-[0.12em] bo-muted">{item.label}</p>
                <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{item.value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
