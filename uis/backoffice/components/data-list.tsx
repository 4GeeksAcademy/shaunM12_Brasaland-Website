export interface DataListRow {
  label: string;
  value: number;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function DataList({
  title,
  rows,
}: {
  title: string;
  rows: DataListRow[];
}): React.JSX.Element {
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
