"""Бенчмарк: надбавка рынка по ставкам МСП к ключевой ставке."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from app.data.records import KeyRatePoint, SmeRatePoint


@dataclass(frozen=True, slots=True)
class Benchmark:
    """Текущая надбавка рынка: ставка МСП минус ключевая."""

    month: str
    sme_rate: float
    key_rate: float
    premium_bp: float


@dataclass(frozen=True, slots=True)
class MonthlyRate:
    """Помесячный ряд для бенчмарка."""

    month: str
    key_rate_avg: float
    sme_rate: float


def _month_key(day: object) -> str:
    return f"{day.year:04d}-{day.month:02d}"  # type: ignore[attr-defined]


def monthly_rates(key_rate: list[KeyRatePoint], sme_rates: list[SmeRatePoint]) -> list[MonthlyRate]:
    """Помесячный ряд: средняя ключевая ставка и ставка МСП за тот же месяц."""
    averages: dict[str, float] = {}
    if key_rate:
        buckets: dict[str, list[float]] = {}
        for point in key_rate:
            buckets.setdefault(_month_key(point.date), []).append(point.rate)
        averages = {month: fmean(values) for month, values in buckets.items()}

    rows: list[MonthlyRate] = []
    for sme in sme_rates:
        average = averages.get(sme.month)
        if average is None:
            continue
        rows.append(MonthlyRate(month=sme.month, key_rate_avg=average, sme_rate=sme.rate))
    return sorted(rows, key=lambda row: row.month)


def build_benchmark(
    key_rate: list[KeyRatePoint], sme_rates: list[SmeRatePoint]
) -> Benchmark | None:
    """Последняя доступная надбавка рынка или None, если данных нет."""
    rows = monthly_rates(key_rate, sme_rates)
    if not rows:
        return None
    last = rows[-1]
    return Benchmark(
        month=last.month,
        sme_rate=last.sme_rate,
        key_rate=last.key_rate_avg,
        premium_bp=(last.sme_rate - last.key_rate_avg) * 100.0,
    )
