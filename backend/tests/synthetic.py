"""Синтетический датасет для тестов сервисов: правило должно иметь понятный lift."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.data.records import KeyRatePoint, OfzCurvePoint, RusfarPoint, SmeRatePoint
from app.data.sources import MoneyDataset

DEFAULT_START = date(2016, 1, 1)
PREMIUM_HIGH_BP = 200.0
PREMIUM_LOW_BP = -50.0
EVERY_NTH_MONTH = 3


@dataclass(frozen=True, slots=True)
class SyntheticSpec:
    """Параметры генерации: начало, длина в месяцах и дата обрезки."""

    months: int = 120
    start: date = DEFAULT_START
    last_day: date | None = None


def _month_start(start: date, index: int) -> date:
    total = (start.year * 12 + start.month - 1) + index
    return date(total // 12, total % 12 + 1, 1)


def _month_end(start: date, index: int) -> date:
    return _month_start(start, index + 1) - timedelta(days=1)


def make_dataset(spec: SyntheticSpec | None = None) -> MoneyDataset:
    """Датасет, в котором рост ключевой ставки предсказуем по премии.

    Каждый третий месяц премия высокая (200 б.п.), и в начале следующего месяца
    ключевая ставка поднимается на 0.5 п.п. В остальные месяцы премия −50 б.п. и
    ставка не меняется, поэтому режим ``z >= 1`` отделяет событие от его отсутствия.
    """
    options = spec or SyntheticSpec()
    key_rate: list[KeyRatePoint] = []
    rusfar: list[RusfarPoint] = []
    ofz: list[OfzCurvePoint] = []
    sme: list[SmeRatePoint] = []

    rate = 10.0
    previous_high = False
    for index in range(options.months):
        month_first = _month_start(options.start, index)
        month_last = _month_end(options.start, index)
        premium = PREMIUM_HIGH_BP if index % EVERY_NTH_MONTH == 0 else PREMIUM_LOW_BP
        if index > 0 and previous_high:
            rate += 0.5
        previous_high = premium > 0

        day = month_first
        while day <= month_last:
            key_rate.append(KeyRatePoint(date=day, rate=rate))
            rusfar.append(RusfarPoint(date=day, rate=rate + premium / 100.0))
            ofz.append(
                OfzCurvePoint(
                    date=day,
                    curve={
                        0.25: rate,
                        1.0: rate + premium / 200.0,
                        3.0: rate + 1.0,
                    },
                )
            )
            day += timedelta(days=1)

        sme.append(
            SmeRatePoint(
                month=f"{month_first.year:04d}-{month_first.month:02d}",
                rate_upto_1y=rate + 4.0,
                rate_over_1y=rate + 3.0,
            )
        )

    if options.last_day is not None:
        key_rate = [point for point in key_rate if point.date <= options.last_day]
        rusfar = [point for point in rusfar if point.date <= options.last_day]
        ofz = [point for point in ofz if point.date <= options.last_day]

    return MoneyDataset(key_rate=key_rate, ofz_curve=ofz, rusfar=rusfar, sme_rates=sme)
