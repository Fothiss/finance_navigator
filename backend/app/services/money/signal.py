"""Сборка ответа `/money/signals`: два независимых сигнала, сравнение, бенчмарк."""

from __future__ import annotations

from datetime import date, timedelta

from app.config.settings import Settings
from app.data.sources import KEY_RATE, OFZ_CURVE, RUSFAR1M, SME_RATES, MoneyDataset
from app.schemas.money import (
    BaselineInfo,
    BenchmarkBlock,
    ComparisonBlock,
    DataFreshness,
    Driver,
    EvidenceBlock,
    Indicator,
    ModelInfo,
    MoneySignals,
    PolicyBlock,
    ProbabilityBlock,
    SignalStatus,
    SignalVariant,
    SourceFreshness,
    Target,
)
from app.services.money.backtest import VariantBacktest, compare_variants, run_backtest
from app.services.money.benchmark import build_benchmark
from app.services.money.indicators import (
    OFZ,
    RUSFAR,
    VARIANT_LABELS,
    VARIANTS,
    PremiumPoint,
    build_premium_series,
    latest_point,
)
from app.services.money.policy import Policy, Verdict, decide
from app.services.money.rule import RuleEstimate, estimate_rule
from app.services.money.target import build_monthly_observations

EVENT = "key_rate_up_forward"
BASELINE_NAME = "unconditional_base_rate"
MODEL_NAME = "rule_zscore_threshold"


def _month_end(month: str) -> date:
    year, number = (int(part) for part in month.split("-"))
    if number == 12:
        return date(year, 12, 31)
    return date(year, number + 1, 1) - timedelta(days=1)


def _source_freshness(dataset: MoneyDataset, cfg: Settings, today: date) -> DataFreshness:
    last = dataset.last_dates()
    daily_allowance = cfg.money_stale_days
    monthly_allowance = cfg.money_stale_days_sme

    sources: list[SourceFreshness] = []
    for name, allowance in (
        (KEY_RATE, daily_allowance),
        (OFZ_CURVE, daily_allowance),
        (RUSFAR1M, daily_allowance),
        (SME_RATES, monthly_allowance),
    ):
        value = last.get(name)
        stale = value is None or (today - value).days > allowance
        sources.append(SourceFreshness(name=name, last_date=value, stale=stale))

    return DataFreshness(
        stale=any(source.stale for source in sources),
        as_of=max((value for value in last.values() if value is not None), default=today),
        sources=sources,
    )


def _indicators(dataset: MoneyDataset, variant: str, point: PremiumPoint | None) -> list[Indicator]:
    rows: list[Indicator] = []
    if dataset.key_rate:
        last_key = dataset.key_rate[-1]
        rows.append(
            Indicator(
                code="key_rate",
                label="Ключевая ставка",
                value=last_key.rate,
                unit="%",
                as_of=last_key.date,
            )
        )
    if variant == RUSFAR and dataset.rusfar:
        last_rusfar = dataset.rusfar[-1]
        rows.append(
            Indicator(
                code="rusfar_1m",
                label="RUSFAR 1M",
                value=last_rusfar.rate,
                unit="%",
                as_of=last_rusfar.date,
            )
        )
    if variant == OFZ and dataset.ofz_curve:
        last_ofz = dataset.ofz_curve[-1]
        ofz_value = last_ofz.tenor(1.0)
        if ofz_value is not None:
            rows.append(
                Indicator(
                    code="ofz_1y",
                    label="ОФЗ 1 год",
                    value=ofz_value,
                    unit="%",
                    as_of=last_ofz.date,
                )
            )
    if point is not None:
        rows.append(
            Indicator(
                code="premium_bp",
                label="Премия за срок",
                value=point.premium_bp,
                unit="б.п.",
                as_of=point.date,
            )
        )
        if point.z_score is not None:
            rows.append(
                Indicator(
                    code="z_score",
                    label="Отклонение от нормы",
                    value=point.z_score,
                    unit="σ",
                    as_of=point.date,
                )
            )
    return rows


def _drivers(point: PremiumPoint | None, threshold: float) -> list[Driver]:
    if point is None or point.z_score is None:
        return []
    elevated = point.z_score >= threshold
    return [
        Driver(
            code="premium_z",
            label=(
                "Премия за срок выше обычного: рынок закладывает ужесточение"
                if elevated
                else "Премия за срок ниже обычного: рынок не ждёт ужесточения"
            ),
            impact="up" if elevated else "down",
            weight=abs(round(point.z_score, 2)),
        )
    ]


def _headline(variant: str, verdict: Verdict | None, point: PremiumPoint) -> str:
    base = (
        f"{VARIANT_LABELS[variant]}: премия к ключевой {point.premium_bp:+.0f} б.п., "
        f"z-score {point.z_score:+.1f}."
    )
    tails = {
        Verdict.borrow_now: (
            " Рынок закладывает ужесточение: если кредит нужен в ближайшие 1–3 месяца, "
            "ставку лучше зафиксировать сейчас."
        ),
        Verdict.wait: (" Рынок не ждёт повышения ставки: решение о займе можно отложить."),
        Verdict.watch: (
            " Признаков ужесточения нет, но и запаса прочности тоже — "
            "ситуацию стоит держать на контроле."
        ),
    }
    return base + tails.get(verdict, "") if verdict is not None else base


def _probability_block(
    variant: str,
    point: PremiumPoint,
    estimate: RuleEstimate,
    cfg: Settings,
) -> ProbabilityBlock | None:
    value = estimate.predict(point.z_score)
    if value is None:
        return None
    bucket = (
        estimate.regime
        if point.z_score is not None and point.z_score >= estimate.threshold
        else estimate.calm
    )
    return ProbabilityBlock(
        event=f"{EVENT}_{cfg.money_forward_days}d",
        horizon_days=cfg.money_forward_days,
        value=round(value, 4),
        interval_80=(
            round(bucket.interval[0], 4) if bucket.interval else 0.0,
            round(bucket.interval[1], 4) if bucket.interval else 1.0,
        ),
        model=ModelInfo(name=f"{MODEL_NAME}_{estimate.threshold:g}", kind="rule"),
        baseline=BaselineInfo(name=BASELINE_NAME, value=round(estimate.baseline, 4)),
        lift=round(value - estimate.baseline, 4),
        n_observations=bucket.n,
        threshold_z=estimate.threshold,
    )


def _evidence(test: VariantBacktest) -> EvidenceBlock:
    return EvidenceBlock(
        status=test.status,
        period_from=test.period_from,
        period_to=test.period_to,
        n_observations=test.n_observations,
        n_regime=test.n_regime,
        hit_rate=None if test.hit_rate is None else round(test.hit_rate, 4),
        baseline_hit_rate=None
        if test.baseline_hit_rate is None
        else round(test.baseline_hit_rate, 4),
        brier=None if test.brier is None else round(test.brier, 4),
        baseline_brier=None if test.baseline_brier is None else round(test.baseline_brier, 4),
        reason=test.reason,
    )


def build_signals(
    dataset: MoneyDataset,
    cfg: Settings,
    policy: Policy,
    today: date | None = None,
) -> MoneySignals:
    """Собрать ответ сигналов: оба варианта считаются на одном периоде."""
    current_day = today or date.today()
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    freshness = _source_freshness(dataset, cfg, current_day)

    default_policy = Policy(
        source="default",
        p_borrow_now=cfg.money_p_borrow_now,
        p_wait=cfg.money_p_wait,
    )

    signals: list[SignalVariant] = []
    backtests: dict[str, VariantBacktest] = {}
    probabilities: dict[str, ProbabilityBlock | None] = {}
    verdicts: dict[str, Verdict | None] = {}

    for variant in VARIANTS:
        point = latest_point(premiums.get(variant, []))
        estimate = estimate_rule(observations, variant, cfg)

        if estimate is None or point is None:
            signals.append(
                SignalVariant(
                    variant=variant,
                    variant_label=VARIANT_LABELS[variant],
                    status=SignalStatus.insufficient_evidence,
                    evidence=EvidenceBlock(
                        status="not_run",
                        reason="нет данных для расчёта правила",
                    ),
                    indicators=_indicators(dataset, variant, point),
                )
            )
            continue

        test = run_backtest(observations, variant, estimate, cfg)
        backtests[variant] = test
        probability = _probability_block(variant, point, estimate, cfg)
        verdict = decide(probability.value if probability else None, policy)
        probabilities[variant] = probability
        verdicts[variant] = verdict

        signals.append(
            SignalVariant(
                variant=variant,
                variant_label=VARIANT_LABELS[variant],
                status=SignalStatus.ok,
                verdict=verdict,
                headline=_headline(variant, verdict, point),
                probability=probability,
                indicators=_indicators(dataset, variant, point),
                drivers=_drivers(point, cfg.money_z_threshold),
                evidence=_evidence(test),
            )
        )

    comparison = compare_variants(backtests, cfg)
    leader = comparison.leader if comparison.leader in probabilities else None
    recommended_source = (
        probabilities.get(leader)
        if leader is not None
        else next(iter(probabilities.values()), None)
    )
    recommended = (
        decide(recommended_source.value, default_policy) if recommended_source is not None else None
    )

    benchmark = build_benchmark(dataset.key_rate, dataset.sme_rates)
    benchmark_block = (
        None
        if benchmark is None
        else BenchmarkBlock(
            month=benchmark.month,
            as_of=_month_end(benchmark.month),
            sme_rate=round(benchmark.sme_rate, 2),
            key_rate=round(benchmark.key_rate, 2),
            premium_bp=round(benchmark.premium_bp, 1),
        )
    )

    status = (
        SignalStatus.ok
        if any(signal.status == SignalStatus.ok for signal in signals)
        else SignalStatus.insufficient_evidence
    )

    return MoneySignals(
        as_of=freshness.as_of,
        status=status,
        target=Target(
            event=f"{EVENT}_{cfg.money_forward_days}d", horizon_days=cfg.money_forward_days
        ),
        policy=PolicyBlock(
            source=policy.source,
            p_borrow_now=policy.p_borrow_now,
            p_wait=policy.p_wait,
            default={
                "p_borrow_now": default_policy.p_borrow_now,
                "p_wait": default_policy.p_wait,
            },
            recommended_verdict=recommended,
        ),
        signals=signals,
        comparison=ComparisonBlock(
            leader=comparison.leader,
            metric=comparison.metric,
            verdict=comparison.verdict,
            by_variant=comparison.by_variant,
        ),
        benchmark=benchmark_block,
        data=freshness,
    )
