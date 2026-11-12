import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SpreadSeries } from "../api/client";

type Row = { date: string } & Record<string, number | string>;

export function mergeSpreads(spreads: SpreadSeries[]): Row[] {
  const rows = new Map<string, Row>();
  for (const series of spreads) {
    for (const point of series.points) {
      const row = rows.get(point.date) ?? { date: point.date };
      row[series.variant] = point.premium_bp;
      rows.set(point.date, row);
    }
  }
  return [...rows.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

type Props = {
  spreads: SpreadSeries[];
};

export function SpreadChart({ spreads }: Props) {
  const rows = mergeSpreads(spreads);
  const last = rows.at(-1);

  return (
    <section className="rounded-lg border border-line p-4" data-testid="spread-chart">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Премия за срок к ключевой ставке, б.п.</h2>
        <span className="text-xs text-muted">точек: {rows.length}</span>
      </header>
      <ul className="mt-1 flex flex-wrap gap-3 text-xs text-muted">
        {spreads.map((series) => (
          <li key={series.variant} data-testid={`legend-${series.variant}`}>
            {series.label}
          </li>
        ))}
      </ul>
      <div className="mt-3 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
            <YAxis tick={{ fontSize: 11 }} unit=" б.п." width={70} />
            <Tooltip formatter={(value: number) => `${value} б.п.`} />
            <Legend />
            <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 4" />
            {spreads.map((series, index) => (
              <Line
                key={series.variant}
                type="monotone"
                dataKey={series.variant}
                name={series.label}
                dot={false}
                strokeWidth={2}
                stroke={index === 0 ? "#1d4ed8" : "#b45309"}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {last ? (
        <p className="mt-2 text-xs text-muted">
          последняя точка: {String(last.date)}
          {spreads.map((series) =>
            last[series.variant] === undefined ? null : (
              <span key={series.variant}>
                {" "}
                · {series.variant}: {String(last[series.variant])} б.п.
              </span>
            ),
          )}
        </p>
      ) : null}
    </section>
  );
}
