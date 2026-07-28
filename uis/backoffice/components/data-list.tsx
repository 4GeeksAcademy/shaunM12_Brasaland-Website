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
    <article className="bo-card">
      <h3 className="bo-eyebrow">{title}</h3>

      {rows.length === 0 ? (
        <p className="mt-4 rounded-md bg-[color:var(--bo-row-bg)] p-3 text-sm bo-muted">No data available.</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {rows.map((row) => (
            <li
              key={row.label}
              className="bo-row"
            >
              <span className="bo-fg-secondary">{row.label}</span>
              <span className="font-semibold text-[color:var(--bo-accent-muted)]">{formatNumber(row.value)}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
