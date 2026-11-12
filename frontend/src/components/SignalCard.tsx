import type { SignalVariant } from "../api/client";

export const VERDICT_LABEL: Record<string, string> = {
  borrow_now: "Фиксировать сейчас",
  watch: "Наблюдать",
  wait: "Можно отложить",
};

const VERDICT_STYLE: Record<string, string> = {
  borrow_now: "bg-red-50 text-red-700 border-red-200",
  watch: "bg-amber-50 text-amber-700 border-amber-200",
  wait: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

type Props = {
  signal: SignalVariant;
  pBorrowNow: number;
  pWait: number;
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function Gauge({ value, pBorrowNow, pWait }: { value: number; pBorrowNow: number; pWait: number }) {
  const clamp = (n: number) => Math.min(100, Math.max(0, n * 100));
  return (
    <div className="mt-3">
      <div className="relative h-2 rounded bg-line">
        <span
          className="absolute top-0 h-2 bg-emerald-300"
          style={{ left: 0, width: `${clamp(pWait)}%` }}
          aria-hidden
        />
        <span
          className="absolute top-0 h-2 bg-amber-300"
          style={{ left: `${clamp(pWait)}%`, width: `${clamp(pBorrowNow) - clamp(pWait)}%` }}
          aria-hidden
        />
        <span
          className="absolute top-0 h-2 bg-red-300"
          style={{ left: `${clamp(pBorrowNow)}%`, width: `${100 - clamp(pBorrowNow)}%` }}
          aria-hidden
        />
        <span
          data-testid="gauge-marker"
          className="absolute -top-1 h-4 w-0.5 bg-ink"
          style={{ left: `${clamp(value)}%` }}
          aria-hidden
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span data-testid="marker-wait">ждать &lt; {percent(pWait)}</span>
        <span data-testid="value-label">p = {percent(value)}</span>
        <span data-testid="marker-borrow">фиксировать ≥ {percent(pBorrowNow)}</span>
      </div>
    </div>
  );
}

export function SignalCard({ signal, pBorrowNow, pWait }: Props) {
  const probability = signal.probability ?? null;

  return (
    <article className="rounded-lg border border-line p-4" data-testid={`signal-${signal.variant}`}>
      <header className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-medium text-muted">{signal.variant_label}</h3>
        {signal.status === "ok" && signal.verdict ? (
          <span className={`rounded-full border px-2 py-0.5 text-xs ${VERDICT_STYLE[signal.verdict]}`}>
            {VERDICT_LABEL[signal.verdict]}
          </span>
        ) : (
          <span className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">
            {signal.status === "stale_data" ? "Данные устарели" : "Недостаточно данных"}
          </span>
        )}
      </header>

      {signal.status === "stale_data" ? (
        <p className="mt-3 text-sm text-muted">
          Источники отстали — вердикт не выдаётся, пока данные не обновятся.
        </p>
      ) : null}

      {signal.status === "insufficient_evidence" ? (
        <p className="mt-3 text-sm text-muted">
          Бэктест не пройден: {signal.evidence.reason ?? "недостаточно истории для проверки правила"}.
          Сигнал не выдаётся, чтобы не подменять измерение догадкой.
        </p>
      ) : null}

      {signal.status === "ok" && probability ? (
        <>
          <p className="mt-3 text-2xl font-semibold">{percent(probability.value)}</p>
          <p className="text-sm text-muted">
            вероятность повышения ключевой за {probability.horizon_days} дней · интервал 80%:{" "}
            {percent(probability.interval_80[0])}…{percent(probability.interval_80[1])}
          </p>
          <Gauge value={probability.value} pBorrowNow={pBorrowNow} pWait={pWait} />
          <p className="mt-3 text-sm text-muted">
            baseline {percent(probability.baseline.value)} · прирост{" "}
            {(probability.lift * 100).toFixed(1)} п.п. · n = {probability.n_observations}
          </p>
          {signal.headline ? <p className="mt-3 text-sm">{signal.headline}</p> : null}
          {signal.indicators && signal.indicators.length > 0 ? (
            <ul className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {signal.indicators.map((indicator) => (
                <li key={indicator.code} className="flex justify-between gap-2">
                  <span className="text-muted">{indicator.label}</span>
                  <span>
                    {indicator.value} {indicator.unit}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
    </article>
  );
}
