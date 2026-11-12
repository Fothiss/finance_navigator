"""Правило вероятности: условная частота события в режиме z-score."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.config.settings import Settings
from app.services.money.target import MonthlyObservation


@dataclass(frozen=True, slots=True)
class Bucket:
    """Статистика одного режима (z >= порога или z < порога)."""

    probability: float | None
    n: int
    interval: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class RuleEstimate:
    """Оценка правила: частоты по двум режимам и безусловная частота."""

    threshold: float
    regime: Bucket
    calm: Bucket
    baseline: float
    n_total: int
    positives: int

    def predict(self, z_score: float | None) -> float | None:
        """Вероятность для текущего z-score: частота соответствующего режима."""
        if z_score is None:
            return None
        bucket = self.regime if z_score >= self.threshold else self.calm
        return bucket.probability


def wilson_interval(successes: int, n: int, confidence: float = 0.80) -> tuple[float, float]:
    """Доверительный интервал Уилсона для доли."""
    if n <= 0:
        return (0.0, 1.0)
    z = _z_for_confidence(confidence)
    p = successes / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def _z_for_confidence(confidence: float) -> float:
    """Двусторонняя квантиль нормального распределения для уровня доверия."""
    table = {0.80: 1.2815515655446004, 0.90: 1.6448536269514722, 0.95: 1.959963984540054}
    return table.get(round(confidence, 2), 1.2815515655446004)


def _bucket(rows: list[MonthlyObservation], positive: int, total: int) -> Bucket:
    if total == 0:
        return Bucket(probability=None, n=0, interval=None)
    return Bucket(
        probability=positive / total,
        n=total,
        interval=wilson_interval(positive, total),
    )


def estimate_rule(
    observations: list[MonthlyObservation], variant: str, cfg: Settings
) -> RuleEstimate | None:
    """Оценить правило для варианта на месячной сетке."""
    sample = [
        row for row in observations if row.target_up is not None and row.z.get(variant) is not None
    ]
    if not sample:
        return None

    positives = sum(1 for row in sample if row.target_up)
    regime_rows = [row for row in sample if row.z[variant] >= cfg.money_z_threshold]
    calm_rows = [row for row in sample if row.z[variant] < cfg.money_z_threshold]

    return RuleEstimate(
        threshold=cfg.money_z_threshold,
        regime=_bucket(
            regime_rows, sum(1 for row in regime_rows if row.target_up), len(regime_rows)
        ),
        calm=_bucket(calm_rows, sum(1 for row in calm_rows if row.target_up), len(calm_rows)),
        baseline=positives / len(sample),
        n_total=len(sample),
        positives=positives,
    )
