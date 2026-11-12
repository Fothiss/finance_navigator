"""Индикаторы модуля 1: премия за срок к ключевой ставке и её z-score."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import fmean, pstdev

from app.config.settings import Settings
from app.data.records import KeyRatePoint
from app.data.sources import MoneyDataset

RUSFAR = "rusfar_term_premium"
OFZ = "ofz_curve_premium"
VARIANTS: tuple[str, ...] = (RUSFAR, OFZ)

VARIANT_LABELS: dict[str, str] = {
    RUSFAR: "Премия денежного рынка (RUSFAR 1M)",
    OFZ: "Премия кривой ОФЗ (1 год)",
}

OFZ_TENOR_YEARS = 1.0


@dataclass(frozen=True, slots=True)
class PremiumPoint:
    """Дневная премия за срок: значение в базисных пунктах и её z-score."""

    date: date
    premium_bp: float
    z_score: float | None


def key_rate_at(dates: list[date], rates: list[float], day: date) -> float | None:
    """Ключевая ставка, действовавшая на дату (последнее известное значение)."""
    index = bisect_right(dates, day) - 1
    if index < 0:
        return None
    return rates[index]


def key_rate_at_horizon(
    dates: list[date], rates: list[float], day: date, forward_days: int
) -> float | None:
    """Ключевая ставка через `forward_days`, если данные покрывают горизонт.

    Возвращает None, если последнее наблюдение раньше горизонта: экстраполировать
    последним известным значением нельзя — событие ещё не наступило.
    """
    horizon = day + timedelta(days=forward_days)
    if not dates or dates[-1] < horizon:
        return None
    index = bisect_right(dates, horizon) - 1
    if index < 0:
        return None
    return rates[index]


def z_scores(values: list[float], window: int) -> list[float | None]:
    """Скользящий z-score: окно заканчивается в текущей точке (без будущего)."""
    result: list[float | None] = []
    min_periods = max(2, window // 2)
    for index, value in enumerate(values):
        start = max(0, index - window + 1)
        chunk = values[start : index + 1]
        if len(chunk) < min_periods:
            result.append(None)
            continue
        mean = fmean(chunk)
        deviation = pstdev(chunk)
        result.append(None if deviation == 0 else (value - mean) / deviation)
    return result


def _premium_points(
    values: list[tuple[date, float]],
    key_rate: list[KeyRatePoint],
    window: int,
) -> list[PremiumPoint]:
    dates = [point.date for point in key_rate]
    rates = [point.rate for point in key_rate]

    raw: list[tuple[date, float]] = []
    for day, value in values:
        base = key_rate_at(dates, rates, day)
        if base is None:
            continue
        raw.append((day, (value - base) * 100.0))

    scores = z_scores([premium for _, premium in raw], window)
    return [
        PremiumPoint(date=day, premium_bp=premium, z_score=score)
        for (day, premium), score in zip(raw, scores, strict=False)
    ]


def build_premium_series(dataset: MoneyDataset, cfg: Settings) -> dict[str, list[PremiumPoint]]:
    """Построить ряды премий по обоим вариантам сигнала."""
    rusfar = [(point.date, point.rate) for point in dataset.rusfar]
    ofz = [
        (point.date, point.tenor(OFZ_TENOR_YEARS))
        for point in dataset.ofz_curve
        if point.tenor(OFZ_TENOR_YEARS) is not None
    ]
    ofz_values = [(day, value) for day, value in ofz if value is not None]
    return {
        RUSFAR: _premium_points(rusfar, dataset.key_rate, cfg.money_z_window),
        OFZ: _premium_points(ofz_values, dataset.key_rate, cfg.money_z_window),
    }


def latest_point(series: list[PremiumPoint]) -> PremiumPoint | None:
    """Последняя точка ряда с рассчитанным z-score."""
    for point in reversed(series):
        if point.z_score is not None:
            return point
    return None
