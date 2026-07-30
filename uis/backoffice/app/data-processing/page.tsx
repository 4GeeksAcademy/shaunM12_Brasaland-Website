import Link from "next/link";
import { DataList } from "@/components/data-list";
import {
  buildDataProcessingDashboard,
  DATA_PROCESSING_COUNTRY_OPTIONS,
} from "@/lib/data-processing";

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
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
    <main className="bo-page">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">Brasaland Data Processing</p>
          <h1 className="mt-2 bo-title">
            Operations Aggregated Reports
          </h1>
          <p className="mt-2 max-w-3xl text-sm bo-muted">
            Shared milestone utility outputs visualized for quick operational review, aligned with the
            website&apos;s warm visual language.
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
                {DATA_PROCESSING_COUNTRY_OPTIONS.map((option) => (
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
                href="/data-processing"
                className="rounded-xl border border-[color:var(--bo-input-border)] px-3 py-2 text-sm bo-fg-secondary transition hover:bg-[color:var(--bo-accent-soft)]"
              >
                Reset
              </Link>
            </div>
          </form>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <article className="bo-stat-info">
            <p className="bo-info-label text-xs uppercase tracking-[0.12em]">Total locations</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">{dashboard.totalLocations}</p>
          </article>
          <article className="bo-stat-accent">
            <p className="text-xs uppercase tracking-[0.12em] text-[color:var(--bo-accent-muted)]">Daily revenue (USD)</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">${dashboard.dailyRevenueUSD}</p>
            <p className="text-xs text-[color:var(--bo-muted)]">COP ${formatNumber(dashboard.dailyRevenueCOP)}</p>
          </article>
          <article className="bo-stat-success">
            <p className="text-xs uppercase tracking-[0.12em] text-[color:var(--bo-success-fg)]">Average ticket (USD)</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-heading)]">${dashboard.averageTicketUSD}</p>
          </article>
          <article className="bo-danger-panel rounded-xl p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-[color:var(--bo-error-fg)]">Miami margin %</p>
            <p className="mt-1 text-3xl font-extrabold text-[color:var(--bo-error-fg)]">{dashboard.miamiMarginPercent}%</p>
            <p className="text-xs text-[color:var(--bo-error-fg)]/80">Waste cost USD ${dashboard.wasteCostUSD}</p>
          </article>
        </section>

        <section className="rounded-2xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)] p-5">
          <h2 className="text-lg font-bold text-[color:var(--bo-accent-muted)]">Context3 Function Checks</h2>
          <p className="mt-1 text-sm bo-muted">
            Collection/search/validation contract outputs from the duplicated data-processing core.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            <article className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] p-3">
              <p className="text-xs uppercase tracking-[0.12em] bo-muted">Sales by location</p>
              <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{dashboard.salesByLocationCount}</p>
            </article>
            <article className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] p-3">
              <p className="text-xs uppercase tracking-[0.12em] bo-muted">Sales on date</p>
              <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{dashboard.salesOnDateCount}</p>
            </article>
            <article className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] p-3">
              <p className="text-xs uppercase tracking-[0.12em] bo-muted">Meat menu items</p>
              <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{dashboard.meatItemsCount}</p>
            </article>
            <article className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] p-3">
              <p className="text-xs uppercase tracking-[0.12em] bo-muted">Active locations</p>
              <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{dashboard.activeLocationsCount}</p>
            </article>
            <article className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] p-3">
              <p className="text-xs uppercase tracking-[0.12em] bo-muted">Capacity search index</p>
              <p className="mt-1 text-2xl font-semibold text-[color:var(--bo-heading)]">{dashboard.capacityBinarySearchIndex}</p>
            </article>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <p className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] px-3 py-2 text-sm bo-fg-secondary">
              Location lookup: {dashboard.locationByIdFound ? "Found" : "Not found"}
            </p>
            <p className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] px-3 py-2 text-sm bo-fg-secondary">
              Menu lookup: {dashboard.menuItemByNameFound ? "Found" : "Not found"}
            </p>
            <p className="rounded-lg border border-[color:var(--bo-input-border)]/70 bg-[color:var(--bo-panel)] px-3 py-2 text-sm bo-fg-secondary">
              Validators: menu {dashboard.menuValidationPassed ? "ok" : "fail"}, sale {dashboard.saleValidationPassed ? "ok" : "fail"}, location {dashboard.locationValidationPassed ? "ok" : "fail"}
            </p>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <DataList title="Locations by country" rows={dashboard.locationsByCountry} />
          <DataList title="Locations by city" rows={dashboard.locationsByCity} />
          <DataList title="Payment method mix" rows={dashboard.paymentMethodMix} />
          <DataList title="Top selling items" rows={dashboard.topSellingItems} />
          <DataList title="Waste by reason" rows={dashboard.wasteByReason} />
          <DataList title="Location performance score" rows={dashboard.locationPerformance} />
          <DataList title="Country revenue (USD)" rows={dashboard.countryRevenueUSD} />
        </section>

        <section className="rounded-2xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-panel)] p-5">
          <h2 className="text-lg font-bold text-[color:var(--bo-accent-muted)]">Currency conversion</h2>
          <p className="mt-1 text-sm bo-muted">
            Daily USD revenue converted at fixed rate to COP: {formatNumber(dashboard.revenueUsdAsCop)}.
          </p>
        </section>
      </div>
    </main>
  );
}
