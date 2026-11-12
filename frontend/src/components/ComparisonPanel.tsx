import type { ComparisonBlock } from "../api/client";

const VERDICT_TEXT: Record<string, string> = {
  stable: "разница устойчивая",
  inconclusive: "разница в пределах шума",
};

const VARIANT_LABEL: Record<string, string> = {
  rusfar_term_premium: "RUSFAR 1M",
  ofz_curve_premium: "ОФЗ 1 год",
};

type Props = {
  comparison: ComparisonBlock;
};

export function ComparisonPanel({ comparison }: Props) {
  const rows = Object.entries(comparison.by_variant);
  const leaderLabel = comparison.leader
    ? (VARIANT_LABEL[comparison.leader] ?? comparison.leader)
    : "нет данных";

  return (
    <section className="rounded-lg border border-line p-4" data-testid="comparison-panel">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">
          Какой индикатор точнее: {comparison.metric === "brier" ? "Brier (меньше — лучше)" : comparison.metric}
        </h2>
        <span className="text-xs text-muted" data-testid="comparison-verdict">
          {VERDICT_TEXT[comparison.verdict] ?? comparison.verdict}
        </span>
      </header>

      <p className="mt-2 text-sm">
        Лидер: <span className="font-medium">{leaderLabel}</span>
      </p>

      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th className="font-normal">вариант</th>
            <th className="font-normal">попадание</th>
            <th className="font-normal">baseline</th>
            <th className="font-normal">Brier</th>
            <th className="font-normal">n</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([variant, metrics]) => (
            <tr key={variant} data-testid={`comparison-${variant}`}>
              <td>{VARIANT_LABEL[variant] ?? variant}</td>
              <td>{formatPercent(metrics.hit_rate)}</td>
              <td>{formatPercent(metrics.baseline_hit_rate)}</td>
              <td>{formatNumber(metrics.brier)}</td>
              <td>{metrics.n ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-2 text-xs text-muted">
        Оценка in-sample: правило проверено на той же истории, на которой настроено.
      </p>
    </section>
  );
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—";
}

function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? value.toFixed(3) : "—";
}
