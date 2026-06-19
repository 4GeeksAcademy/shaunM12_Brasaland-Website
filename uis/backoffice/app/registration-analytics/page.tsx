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
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Brasa Points Registration Analytics</p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Registration Aggregated Reports
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Brasa Points loyalty signup analytics. Sourced from registration data only, kept separate
            from operations reporting.
          </p>
        </header>

        <section className="rounded-2xl border border-amber-200/20 bg-stone-900/85 p-5">
          <form className="grid gap-4 md:grid-cols-3" method="get">
            <label className="text-sm text-stone-100">
              Country scope
              <select
                name="country"
                defaultValue={dashboard.countryFilter}
                className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
              >
                {REGISTRATION_COUNTRY_OPTIONS.map((option) => (
                  <option key={option} value={option === "All" ? "" : option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm text-stone-100">
              Reference date
              <input
                type="date"
                name="referenceDate"
                defaultValue={dashboard.referenceDate}
                className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
              />
            </label>

            <div className="flex items-end gap-2">
              <button
                type="submit"
                className="w-full rounded-xl border border-amber-300 bg-amber-300/15 px-3 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25"
              >
                Refresh reports
              </button>
              <Link
                href="/registration-analytics"
                className="rounded-xl border border-stone-600 px-3 py-2 text-sm text-stone-200 transition hover:bg-stone-800"
              >
                Reset
              </Link>
            </div>
          </form>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-emerald-500/30 bg-emerald-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-emerald-200">Total registrations</p>
            <p className="mt-1 text-3xl font-extrabold text-emerald-100">{dashboard.totalRegistrations}</p>
          </article>

          <article className="rounded-xl border border-amber-500/30 bg-amber-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-amber-200">Email opt-in rate</p>
            <p className="mt-1 text-3xl font-extrabold text-amber-100">{dashboard.emailOptInRate}%</p>
            <p className="text-xs text-amber-200/80">{dashboard.emailOptInCount} registrations opted in</p>
          </article>

          <article className="rounded-xl border border-fuchsia-500/30 bg-fuchsia-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-fuchsia-200">Average age</p>
            <p className="mt-1 text-3xl font-extrabold text-fuchsia-100">{dashboard.ageAverage}</p>
            <p className="text-xs text-fuchsia-200/80">
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

        <section className="rounded-2xl border border-amber-200/20 bg-stone-950/70 p-5">
          <h2 className="text-lg font-bold text-amber-200">City registration summary</h2>
          <p className="mt-1 text-sm text-stone-300">
            Numeric summary generated with shared utility functions for deterministic reporting.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {dashboard.cityRegistrationSummary.map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-stone-700/80 bg-stone-900/80 p-3"
              >
                <p className="text-xs uppercase tracking-[0.12em] text-stone-400">{item.label}</p>
                <p className="mt-1 text-2xl font-semibold text-amber-100">{item.value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
