import type {
  BenchmarkBlock,
  ComparisonBlock,
  MoneySignals,
  PoliciesResponse,
  SeriesResponse,
  SignalVariant,
} from "../src/api/client";

export const policiesFixture: PoliciesResponse = {
  policies: [
    { id: "careful", label: "Осторожная", p_borrow_now: 0.8, p_wait: 0.55, is_default: false },
    { id: "balanced", label: "Сбалансированная", p_borrow_now: 0.65, p_wait: 0.45, is_default: true },
    { id: "aggressive", label: "Агрессивная", p_borrow_now: 0.5, p_wait: 0.3, is_default: false },
  ],
  default: { p_borrow_now: 0.65, p_wait: 0.45 },
};

export function makeSignal(overrides: Partial<SignalVariant> = {}): SignalVariant {
  return {
    variant: "rusfar_term_premium",
    variant_label: "Премия денежного рынка (RUSFAR 1M)",
    status: "ok",
    verdict: "watch",
    headline: "Премия в обычном диапазоне",
    probability: {
      event: "key_rate_up_forward_30d",
      horizon_days: 30,
      value: 0.55,
      interval_80: [0.4, 0.7],
      model: { name: "rule_zscore_threshold_1", kind: "rule" },
      baseline: { name: "unconditional_base_rate", value: 0.5 },
      lift: 0.05,
      n_observations: 28,
      threshold_z: 1,
    },
    indicators: [
      { code: "key_rate", label: "Ключевая ставка", value: 14, unit: "%", as_of: "2026-11-12" },
    ],
    drivers: [{ code: "premium_z", label: "премия выше обычного", impact: "up", weight: 1.2 }],
    evidence: {
      status: "passed",
      period_from: "2019-04-30",
      period_to: "2026-10-31",
      n_observations: 90,
      n_regime: 28,
      hit_rate: 0.7,
      baseline_hit_rate: 0.6,
      brier: 0.18,
      baseline_brier: 0.2,
      reason: null,
    },
    ...overrides,
  };
}

export const comparisonFixture: ComparisonBlock = {
  leader: "ofz_curve_premium",
  metric: "brier",
  verdict: "stable",
  by_variant: {
    rusfar_term_premium: { hit_rate: 0.7, baseline_hit_rate: 0.6, brier: 0.18, baseline_brier: 0.2, n: 84 },
    ofz_curve_premium: { hit_rate: 0.82, baseline_hit_rate: 0.76, brier: 0.14, baseline_brier: 0.18, n: 90 },
  },
};

export const benchmarkFixture: BenchmarkBlock = {
  month: "2026-08",
  as_of: "2026-08-31",
  sme_rate: 14.22,
  key_rate: 14.0,
  premium_bp: 22.0,
};

export function makeSignals(overrides: Partial<MoneySignals> = {}): MoneySignals {
  return {
    as_of: "2026-11-12",
    status: "ok",
    target: { event: "key_rate_up_forward_30d", horizon_days: 30 },
    policy: {
      source: "default",
      p_borrow_now: 0.65,
      p_wait: 0.45,
      default: { p_borrow_now: 0.65, p_wait: 0.45 },
      recommended_verdict: "watch",
    },
    signals: [makeSignal(), makeSignal({ variant: "ofz_curve_premium", variant_label: "Премия кривой ОФЗ (1 год)" })],
    comparison: comparisonFixture,
    benchmark: benchmarkFixture,
    data: {
      stale: false,
      as_of: "2026-11-12",
      sources: [
        { name: "cbr_key_rate", last_date: "2026-11-12", stale: false },
        { name: "moex_rusfar1m", last_date: "2026-11-11", stale: false },
      ],
    },
    ...overrides,
  };
}

export const seriesFixture: SeriesResponse = {
  bucket: "week",
  spreads: [
    {
      variant: "rusfar_term_premium",
      label: "Премия денежного рынка (RUSFAR 1M)",
      points: [
        { date: "2026-11-02", premium_bp: -28, z_score: -0.8 },
        { date: "2026-11-09", premium_bp: -30, z_score: -0.91 },
      ],
    },
    {
      variant: "ofz_curve_premium",
      label: "Премия кривой ОФЗ (1 год)",
      points: [
        { date: "2026-11-02", premium_bp: -22, z_score: -0.5 },
        { date: "2026-11-09", premium_bp: -25, z_score: -0.64 },
      ],
    },
  ],
  rates: [
    { month: "2026-07", key_rate_avg: 14.5, sme_rate: 14.6 },
    { month: "2026-08", key_rate_avg: 14.0, sme_rate: 14.22 },
  ],
  meta: {
    spread_last_date: "2026-11-09",
    rates_last_month: "2026-08",
    sources: ["cbr_key_rate", "cbr_ofz_curve", "cbr_sme_rates", "moex_rusfar1m"],
  },
};
