"""Таргет модуля 1: событие «ключевая ставка через 30 дней выше текущей»."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.config.settings import Settings
from app.services.money.indicators import (
    VARIANTS,
    PremiumPoint,
    key_rate_at,
    key_rate_at_horizon,
)


@dataclass(frozen=True, slots=True)
class MonthlyObservation:
    """Наблюдение на конец месяца: премии на дату и событие горизонта."""

    date: date
    key_rate: float
    target_up: bool | None
    z: dict[str, float | None]


def build_monthly_observations(
    key_rate: list,
    premiums: dict[str, list[PremiumPoint]],
    cfg: Settings,
) -> list[MonthlyObservation]:
    """Собрать месячную сетку наблюдений по общей для обоих вариантов истории.

    Сетка берётся из пересечения дат двух премий: сравнение вариантов должно идти
    на одном периоде. Конец месяца — последняя дата месяца в этом пересечении.
    """
    by_variant: dict[str, dict[date, float]] = {
        variant: {point.date: point.z_score for point in premiums.get(variant, [])}
        for variant in VARIANTS
    }
    common: set[date] = set()
    first = True
    for variant in VARIANTS:
        dates = set(by_variant[variant])
        common = dates if first else common & dates
        first = False
    if not common:
        return []

    month_last: dict[tuple[int, int], date] = {}
    for day in sorted(common):
        month_last[(day.year, day.month)] = day

    kr_dates = [point.date for point in key_rate]
    kr_rates = [point.rate for point in key_rate]

    observations: list[MonthlyObservation] = []
    for day in sorted(month_last.values()):
        current = key_rate_at(kr_dates, kr_rates, day)
        if current is None:
            continue
        horizon_rate = key_rate_at_horizon(kr_dates, kr_rates, day, cfg.money_forward_days)
        target = None if horizon_rate is None else horizon_rate > current
        observations.append(
            MonthlyObservation(
                date=day,
                key_rate=current,
                target_up=target,
                z={variant: by_variant[variant].get(day) for variant in VARIANTS},
            )
        )
    return observations
