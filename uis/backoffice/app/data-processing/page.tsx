import Link from "next/link";
import {
  buildDataProcessingDashboard,
  ChartDatum,
  DATA_PROCESSING_COUNTRY_OPTIONS,
} from "@/lib/data-processing";

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function DataList({ title, rows }: { title: string; rows: ChartDatum[] }): React.JSX.Element {
  return (
    <article className="rounded-2xl border border-amber-200/20 bg-stone-950/70 p-5 shadow-xl shadow-black/20">
      <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-amber-300">{title}</h3>

      {rows.length === 0 ? (
        <p className="mt-4 rounded-md bg-stone-900/70 p-3 text-sm text-stone-300">No data available.</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {rows.map((row) => (
            <li
              key={row.label}
              className="flex items-center justify-between rounded-lg border border-stone-700/60 bg-stone-900/80 px-3 py-2 text-sm"
            >
              <span className="text-stone-200">{row.label}</span>
              <span className="font-semibold text-amber-200">{formatNumber(row.value)}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export default async function DataProcessingPage({
  searchParams,
}: {
  searchParams?: Promise<{ country?: string; referenceDate?: string }>;
}): Promise<React.JSX.Element> {
  const resolvedSearchParams = await searchParams;
  const dashboard = buildDataProcessingDashboard({
    country: resolvedSearchParams?.country,
    referenceDate: resolvedSearchParams?.referenceDate,
  });

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Brasaland Data Processing</p>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/incidents"
                className="rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
              >
                Incidents
              </Link>
              <Link
                href="/"
                className="rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
              >
                Back to candidate tracker
              </Link>
            </div>
          </div>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Operations Aggregated Reports
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Shared milestone utility outputs visualized for quick operational review, aligned with the
            website&apos;s warm visual language.
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
                {DATA_PROCESSING_COUNTRY_OPTIONS.map((option) => (
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
                href="/data-processing"
                className="rounded-xl border border-stone-600 px-3 py-2 text-sm text-stone-200 transition hover:bg-stone-800"
              >
                Reset
              </Link>
            </div>
          </form>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <article className="rounded-xl border border-emerald-500/30 bg-emerald-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-emerald-200">Total registrations</p>
            <p className="mt-1 text-3xl font-extrabold text-emerald-100">{dashboard.totalRegistrations}</p>
          </article>

          <article className="rounded-xl border border-cyan-500/30 bg-cyan-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-cyan-200">Total locations</p>
            <p className="mt-1 text-3xl font-extrabold text-cyan-100">{dashboard.totalLocations}</p>
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

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-sky-500/30 bg-sky-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-sky-200">Daily revenue (USD)</p>
            <p className="mt-1 text-3xl font-extrabold text-sky-100">${dashboard.dailyRevenueUSD}</p>
            <p className="text-xs text-sky-200/80">COP ${formatNumber(dashboard.dailyRevenueCOP)}</p>
          </article>
          <article className="rounded-xl border border-lime-500/30 bg-lime-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-lime-200">Average ticket (USD)</p>
            <p className="mt-1 text-3xl font-extrabold text-lime-100">${dashboard.averageTicketUSD}</p>
          </article>
          <article className="rounded-xl border border-rose-500/30 bg-rose-900/20 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-rose-200">Miami margin %</p>
            <p className="mt-1 text-3xl font-extrabold text-rose-100">{dashboard.miamiMarginPercent}%</p>
            <p className="text-xs text-rose-200/80">Waste cost USD ${dashboard.wasteCostUSD}</p>
          </article>
        </section>

        <section className="rounded-2xl border border-amber-200/20 bg-stone-900/80 p-5">
          <h2 className="text-lg font-bold text-amber-200">Context3 Function Checks</h2>
          <p className="mt-1 text-sm text-stone-300">
            Collection/search/validation contract outputs from the duplicated data-processing core.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            <article className="rounded-lg border border-stone-700/70 bg-stone-950/70 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-stone-400">Sales by location</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">{dashboard.salesByLocationCount}</p>
            </article>
            <article className="rounded-lg border border-stone-700/70 bg-stone-950/70 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-stone-400">Sales on date</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">{dashboard.salesOnDateCount}</p>
            </article>
            <article className="rounded-lg border border-stone-700/70 bg-stone-950/70 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-stone-400">Meat menu items</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">{dashboard.meatItemsCount}</p>
            </article>
            <article className="rounded-lg border border-stone-700/70 bg-stone-950/70 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-stone-400">Active locations</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">{dashboard.activeLocationsCount}</p>
            </article>
            <article className="rounded-lg border border-stone-700/70 bg-stone-950/70 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-stone-400">Capacity search index</p>
              <p className="mt-1 text-2xl font-semibold text-amber-100">{dashboard.capacityBinarySearchIndex}</p>
            </article>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <p className="rounded-lg border border-stone-700/70 bg-stone-950/70 px-3 py-2 text-sm text-stone-200">
              Location lookup: {dashboard.locationByIdFound ? "Found" : "Not found"}
            </p>
            <p className="rounded-lg border border-stone-700/70 bg-stone-950/70 px-3 py-2 text-sm text-stone-200">
              Menu lookup: {dashboard.menuItemByNameFound ? "Found" : "Not found"}
            </p>
            <p className="rounded-lg border border-stone-700/70 bg-stone-950/70 px-3 py-2 text-sm text-stone-200">
              Validators: menu {dashboard.menuValidationPassed ? "ok" : "fail"}, sale {dashboard.saleValidationPassed ? "ok" : "fail"}, location {dashboard.locationValidationPassed ? "ok" : "fail"}
            </p>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <DataList title="Registrations by country" rows={dashboard.registrationsByCountry} />
          <DataList title="Registrations by city" rows={dashboard.registrationsByCity} />
          <DataList
            title="Discovery channels"
            rows={dashboard.registrationsByDiscoveryChannel}
          />
          <DataList
            title="Dietary preference selections"
            rows={dashboard.dietaryPreferenceSelections}
          />
          <DataList title="Locations by country" rows={dashboard.locationsByCountry} />
          <DataList title="Locations by city" rows={dashboard.locationsByCity} />
          <DataList title="Payment method mix" rows={dashboard.paymentMethodMix} />
          <DataList title="Top selling items" rows={dashboard.topSellingItems} />
          <DataList title="Waste by reason" rows={dashboard.wasteByReason} />
          <DataList title="Location performance score" rows={dashboard.locationPerformance} />
          <DataList title="Country revenue (USD)" rows={dashboard.countryRevenueUSD} />
        </section>

        <section className="rounded-2xl border border-amber-200/20 bg-stone-950/70 p-5">
          <h2 className="text-lg font-bold text-amber-200">City registration summary</h2>
          <p className="mt-1 text-sm text-stone-300">
            Numeric summary generated with shared utility functions for deterministic reporting.
          </p>
          <p className="mt-1 text-sm text-stone-400">
            Daily USD revenue converted at fixed rate to COP: {formatNumber(dashboard.revenueUsdAsCop)}.
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
