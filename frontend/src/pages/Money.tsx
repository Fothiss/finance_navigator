import { useMemo } from "react";
import { BenchmarkPanel } from "../components/BenchmarkPanel";
import { ComparisonPanel } from "../components/ComparisonPanel";
import { PolicySelect } from "../components/PolicySelect";
import { SignalCard } from "../components/SignalCard";
import { SpreadChart } from "../components/SpreadChart";
import { StaleBanner } from "../components/StaleBanner";
import { useMoneySeries } from "../hooks/useMoneySeries";
import { useMoneySignals } from "../hooks/useMoneySignals";
import { usePolicies } from "../hooks/usePolicies";
import { usePolicyState } from "../hooks/usePolicyState";
import { toPolicyParams } from "../store/policy";

function isoDay(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export default function Money() {
  const policies = usePolicies();
  const { state, update } = usePolicyState(policies.data?.policies.find((p) => p.is_default)?.id);
  const signals = useMoneySignals(toPolicyParams(state));

  const range = useMemo(() => {
    const to = new Date();
    const from = new Date(to.getTime() - 365 * 24 * 60 * 60 * 1000);
    return { from: isoDay(from), to: isoDay(to), bucket: "week" as const };
  }, []);
  const series = useMoneySeries(range);

  const thresholds = signals.data
    ? { pBorrowNow: signals.data.policy.p_borrow_now, pWait: signals.data.policy.p_wait }
    : { pBorrowNow: 0.65, pWait: 0.45 };
  const defaultThresholds = policies.data
    ? {
        pBorrowNow: policies.data.default.p_borrow_now ?? 0.65,
        pWait: policies.data.default.p_wait ?? 0.45,
      }
    : { pBorrowNow: 0.65, pWait: 0.45 };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Стоимость денег</h1>
          <p className="text-sm text-muted">
            Два независимых сигнала о вероятности повышения ключевой ставки за 30 дней.
          </p>
        </div>
        <div className="text-right text-sm">
          {signals.data ? (
            <>
              <div className="text-muted">данные на {signals.data.as_of}</div>
              <div className="text-xs text-muted">политика: {signals.data.policy.source}</div>
              {signals.data.policy.source !== "default" && signals.data.policy.recommended_verdict ? (
                <div className="text-xs text-amber-700">
                  политика изменена · по умолчанию было бы: {signals.data.policy.recommended_verdict}
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </header>

      {signals.data ? <StaleBanner stale={signals.data.data.stale} sources={signals.data.data.sources} /> : null}

      {signals.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
          <p className="font-medium">
            Ошибка {signals.error.status}: {signals.error.problem.title ?? "запрос не выполнен"}
          </p>
          <p>{signals.error.problem.detail ?? "попробуйте позже"}</p>
        </div>
      ) : null}

      {policies.data ? (
        <PolicySelect
          policies={policies.data.policies}
          state={state}
          onChange={update}
          defaultThresholds={defaultThresholds}
        />
      ) : null}

      {signals.loading && !signals.data ? <p className="text-sm text-muted">Считаем сигналы…</p> : null}

      {signals.data ? (
        <div className="grid gap-4 md:grid-cols-2">
          {signals.data.signals.map((signal) => (
            <SignalCard
              key={signal.variant}
              signal={signal}
              pBorrowNow={thresholds.pBorrowNow}
              pWait={thresholds.pWait}
            />
          ))}
        </div>
      ) : null}

      {signals.data ? <ComparisonPanel comparison={signals.data.comparison} /> : null}

      {series.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
          Серии не загрузились: {series.error.problem.detail ?? series.error.message}
        </div>
      ) : null}

      {series.data ? (
        <>
          <SpreadChart spreads={series.data.spreads} />
          <BenchmarkPanel benchmark={signals.data?.benchmark} rates={series.data.rates} />
        </>
      ) : null}
    </div>
  );
}
