import type { BenchmarkBlock, RatesPoint } from "../api/client";

type Props = {
  benchmark: BenchmarkBlock | null | undefined;
  rates: RatesPoint[];
};

export function BenchmarkPanel({ benchmark, rates }: Props) {
  return (
    <section className="rounded-lg border border-line p-4" data-testid="benchmark-panel">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Надбавка рынка: ставка МСП к ключевой</h2>
        <span className="text-xs text-muted">месяцев в ряду: {rates.length}</span>
      </header>

      {benchmark ? (
        <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-muted">Ставка МСП</dt>
            <dd className="text-lg font-semibold">{benchmark.sme_rate}%</dd>
          </div>
          <div>
            <dt className="text-muted">Ключевая ставка</dt>
            <dd className="text-lg font-semibold">{benchmark.key_rate}%</dd>
          </div>
          <div>
            <dt className="text-muted">Надбавка</dt>
            <dd className="text-lg font-semibold">{benchmark.premium_bp} б.п.</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-3 text-sm text-muted">Данные по ставкам МСП пока недоступны.</p>
      )}

      {benchmark ? (
        <p className="mt-2 text-xs text-muted">
          месяц: {benchmark.month} · это сравнение, а не прогноз: надбавка показывает, сколько рынок
          берёт сверх ключевой ставки.
        </p>
      ) : null}

      {rates.length > 0 ? (
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="font-normal">месяц</th>
              <th className="font-normal">ключевая</th>
              <th className="font-normal">МСП</th>
            </tr>
          </thead>
          <tbody>
            {rates.slice(-6).map((row) => (
              <tr key={row.month}>
                <td>{row.month}</td>
                <td>{row.key_rate_avg}%</td>
                <td>{row.sme_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
