"""Единая точка загрузки данных модуля 1: ключи кеша и история."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.clients.cbr_client import CbrClient
from app.clients.moex_client import MoexClient
from app.config.settings import Settings
from app.data.cache import SnapshotCache
from app.data.records import KeyRatePoint, OfzCurvePoint, RusfarPoint, SmeRatePoint

KEY_RATE = "cbr_key_rate"
OFZ_CURVE = "cbr_ofz_curve"
RUSFAR1M = "moex_rusfar1m"
SME_RATES = "cbr_sme_rates"


@dataclass(frozen=True, slots=True)
class MoneyDataset:
    """Снимок внешних данных, с которым работают сервисы модуля 1."""

    key_rate: list[KeyRatePoint]
    ofz_curve: list[OfzCurvePoint]
    rusfar: list[RusfarPoint]
    sme_rates: list[SmeRatePoint]

    def last_dates(self) -> dict[str, date | None]:
        """Последняя доступная дата по каждому источнику."""
        return {
            KEY_RATE: self.key_rate[-1].date if self.key_rate else None,
            OFZ_CURVE: self.ofz_curve[-1].date if self.ofz_curve else None,
            RUSFAR1M: self.rusfar[-1].date if self.rusfar else None,
            SME_RATES: _month_end(self.sme_rates[-1].month) if self.sme_rates else None,
        }


def _month_end(month: str) -> date:
    year, month_number = (int(part) for part in month.split("-"))
    if month_number == 12:
        return date(year, 12, 31)
    return date(year, month_number + 1, 1) - timedelta(days=1)


def history_start(today: date, years: int) -> date:
    """Начало окна истории: `years` лет назад от сегодня."""
    return today - timedelta(days=365 * years)


def load_dataset(
    cache: SnapshotCache,
    cfg: Settings,
    cbr: CbrClient,
    moex: MoexClient,
    today: date | None = None,
) -> MoneyDataset:
    """Загрузить все источники модуля 1 через кеш."""
    current = today or date.today()
    start = history_start(current, cfg.money_history_years)
    return MoneyDataset(
        key_rate=cache.get_or_load(
            KEY_RATE, lambda: cbr.fetch_key_rate(start, current), KeyRatePoint
        ),
        ofz_curve=cache.get_or_load(
            OFZ_CURVE, lambda: cbr.fetch_ofz_curve(start, current), OfzCurvePoint
        ),
        rusfar=cache.get_or_load(
            RUSFAR1M, lambda: moex.fetch_rusfar1m(start, current), RusfarPoint
        ),
        sme_rates=cache.get_or_load(SME_RATES, cbr.fetch_sme_rates, SmeRatePoint),
    )
