"""Бэктест правила и сравнение вариантов между собой."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.config.settings import Settings
from app.services.money.rule import RuleEstimate
from app.services.money.target import MonthlyObservation


class BacktestStatus(StrEnum):
    passed = "passed"
    failed = "failed"
    not_run = "not_run"


@dataclass(frozen=True, slots=True)
class VariantBacktest:
    """Метрики одного варианта на общем периоде."""

    status: BacktestStatus
    period_from: date | None
    period_to: date | None
    n_observations: int
    n_regime: int
    hit_rate: float | None
    baseline_hit_rate: float | None
    brier: float | None
    baseline_brier: float | None
    lift: float | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Comparison:
    """Сравнение вариантов по одной метрике."""

    leader: str | None
    metric: str
    verdict: str
    by_variant: dict[str, dict[str, float | int | None]]


def _brier(predictions: list[float], outcomes: list[int]) -> float | None:
    if not predictions:
        return None
    return sum((p - y) ** 2 for p, y in zip(predictions, outcomes, strict=True)) / len(predictions)


def _hit_rate(predictions: list[float], outcomes: list[int]) -> float | None:
    if not predictions:
        return None
    hits = sum(1 for p, y in zip(predictions, outcomes, strict=True) if int(p >= 0.5) == y)
    return hits / len(predictions)


def run_backtest(
    observations: list[MonthlyObservation],
    variant: str,
    estimate: RuleEstimate,
    cfg: Settings,
) -> VariantBacktest:
    """Посчитать метрики варианта и решить, можно ли выдавать сигнал."""
    sample = [
        row for row in observations if row.target_up is not None and row.z.get(variant) is not None
    ]
    if not sample:
        return VariantBacktest(
            status=BacktestStatus.not_run,
            period_from=None,
            period_to=None,
            n_observations=0,
            n_regime=estimate.regime.n,
            hit_rate=None,
            baseline_hit_rate=None,
            brier=None,
            baseline_brier=None,
            lift=None,
            reason="нет наблюдений с известным исходом",
        )

    outcomes = [1 if row.target_up else 0 for row in sample]
    predictions: list[float] = []
    for row in sample:
        predicted = estimate.predict(row.z[variant])
        predictions.append(estimate.baseline if predicted is None else predicted)

    lift_regime = (
        None
        if estimate.regime.probability is None
        else estimate.regime.probability - estimate.baseline
    )
    lift_calm = (
        None if estimate.calm.probability is None else estimate.calm.probability - estimate.baseline
    )
    strongest_lift = max(
        (abs(value) for value in (lift_regime, lift_calm) if value is not None),
        default=0.0,
    )

    status = BacktestStatus.passed
    reason: str | None = None
    if len(sample) < cfg.money_min_observations:
        status = BacktestStatus.failed
        reason = f"мало наблюдений: {len(sample)} < {cfg.money_min_observations}"
    elif estimate.regime.n == 0:
        status = BacktestStatus.failed
        reason = "ни один месяц не попал в режим повышенной премии"
    elif strongest_lift < cfg.money_min_lift:
        status = BacktestStatus.failed
        reason = f"прирост к baseline ниже порога: {strongest_lift:.3f} < {cfg.money_min_lift}"

    return VariantBacktest(
        status=status,
        period_from=sample[0].date,
        period_to=sample[-1].date,
        n_observations=len(sample),
        n_regime=estimate.regime.n,
        hit_rate=_hit_rate(predictions, outcomes),
        baseline_hit_rate=_hit_rate([estimate.baseline] * len(sample), outcomes),
        brier=_brier(predictions, outcomes),
        baseline_brier=_brier([estimate.baseline] * len(sample), outcomes),
        lift=lift_regime,
        reason=reason,
    )


def compare_variants(backtests: dict[str, VariantBacktest], cfg: Settings) -> Comparison:
    """Сравнить варианты по Brier: меньшая метрика лучше."""
    scored = {name: test for name, test in backtests.items() if test.brier is not None}
    by_variant = {
        name: {
            "hit_rate": test.hit_rate,
            "baseline_hit_rate": test.baseline_hit_rate,
            "brier": test.brier,
            "baseline_brier": test.baseline_brier,
            "n": test.n_observations,
        }
        for name, test in backtests.items()
    }

    if not scored:
        return Comparison(
            leader=None, metric="brier", verdict="inconclusive", by_variant=by_variant
        )

    leader = min(scored, key=lambda name: scored[name].brier or 0.0)
    if len(scored) < 2:
        return Comparison(
            leader=leader, metric="brier", verdict="inconclusive", by_variant=by_variant
        )

    others = [
        test.brier for name, test in scored.items() if name != leader and test.brier is not None
    ]
    runner_up = min(others)
    margin = (scored[leader].brier or 0.0) - runner_up
    verdict = "stable" if abs(margin) >= cfg.money_comparison_margin else "inconclusive"
    return Comparison(leader=leader, metric="brier", verdict=verdict, by_variant=by_variant)
