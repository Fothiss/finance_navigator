"""Сборка ответа `/money/series`: премии обоих вариантов и помесячные ставки."""

from __future__ import annotations

from datetime import date

from app.config.settings import Settings
from app.data.sources import MoneyDataset
from app.schemas.money import (
    RatesPoint,
    SeriesMeta,
    SeriesResponse,
    SpreadSeries,
    SpreadSeriesPoint,
)
from app.services.money.benchmark import monthly_rates
from app.services.money.indicators import (
    VARIANT_LABELS,
    VARIANTS,
    PremiumPoint,
    build_premium_series,
)

BUCKETS = ("day", "week", "month")


def bucket_key(day: date, bucket: str) -> tuple[int, int]:
    """Ключ бакета: день, ISO-неделя или месяц."""
    if bucket == "day":
        return (day.toordinal(), 0)
    if bucket == "week":
        iso = day.isocalendar()
        return (iso.year, iso.week)
    return (day.year, day.month)


def bucketize(points: list[PremiumPoint], bucket: str) -> list[PremiumPoint]:
    """Оставить последнюю точку каждого бакета (порядок сохраняется)."""
    if bucket not in BUCKETS:
        raise ValueError(f"неизвестный бакет: {bucket}")
    if bucket == "day":
        return list(points)
    last: dict[tuple[int, int], PremiumPoint] = {}
    for point in points:
        last[bucket_key(point.date, bucket)] = point
    return [last[key] for key in sorted(last)]


def _in_range(day: date, date_from: date, date_to: date) -> bool:
    return date_from <= day <= date_to


def build_series(
    dataset: MoneyDataset,
    cfg: Settings,
    date_from: date,
    date_to: date,
    bucket: str = "week",
) -> SeriesResponse:
    """Собрать серии: дневные премии (с бакетом) и помесячные ставки."""
    premiums = build_premium_series(dataset, cfg)

    spreads: list[SpreadSeries] = []
    spread_last: date | None = None
    for variant in VARIANTS:
        points = [
            point
            for point in premiums.get(variant, [])
            if _in_range(point.date, date_from, date_to)
        ]
        if points:
            spread_last = max(spread_last, points[-1].date) if spread_last else points[-1].date
        spreads.append(
            SpreadSeries(
                variant=variant,
                label=VARIANT_LABELS[variant],
                points=[
                    SpreadSeriesPoint(
                        date=point.date,
                        premium_bp=round(point.premium_bp, 2),
                        z_score=None if point.z_score is None else round(point.z_score, 3),
                    )
                    for point in bucketize(points, bucket)
                ],
            )
        )

    rates = [
        RatesPoint(
            month=row.month,
            key_rate_avg=round(row.key_rate_avg, 2),
            sme_rate=round(row.sme_rate, 2),
        )
        for row in monthly_rates(dataset.key_rate, dataset.sme_rates)
        if _in_range(date.fromisoformat(f"{row.month}-01"), date_from, date_to)
    ]

    return SeriesResponse(
        bucket=bucket,
        spreads=spreads,
        rates=rates,
        meta=SeriesMeta(
            spread_last_date=spread_last,
            rates_last_month=rates[-1].month if rates else None,
            sources=sorted(
                name
                for name, values in (
                    ("cbr_key_rate", dataset.key_rate),
                    ("cbr_ofz_curve", dataset.ofz_curve),
                    ("moex_rusfar1m", dataset.rusfar),
                    ("cbr_sme_rates", dataset.sme_rates),
                )
                if values
            ),
        ),
    )
