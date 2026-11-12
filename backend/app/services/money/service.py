"""Фасад сервисов модуля 1: единая точка для роутеров."""

from __future__ import annotations

from datetime import date

from app.clients.cbr_client import CbrClient
from app.clients.moex_client import MoexClient
from app.config.settings import Settings
from app.data.cache import SnapshotCache
from app.data.sources import MoneyDataset, load_dataset
from app.schemas.money import MoneySignals, PoliciesResponse, PolicyItem, SeriesResponse
from app.services.money.policy import PRESET_LABELS, Policy
from app.services.money.series import build_series
from app.services.money.signal import build_signals


class MoneyService:
    """Загружает данные через кеш и собирает ответы API."""

    def __init__(
        self,
        cfg: Settings,
        cache: SnapshotCache,
        cbr: CbrClient,
        moex: MoexClient,
        today: date | None = None,
    ) -> None:
        self._cfg = cfg
        self._cache = cache
        self._cbr = cbr
        self._moex = moex
        self._today = today

    @property
    def today(self) -> date:
        return self._today or date.today()

    def dataset(self) -> MoneyDataset:
        """Данные модуля 1 (кеш с TTL и снапшотом)."""
        return load_dataset(self._cache, self._cfg, self._cbr, self._moex, today=self.today)

    def get_signals(self, policy: Policy) -> MoneySignals:
        return build_signals(self.dataset(), self._cfg, policy, today=self.today)

    def get_series(self, date_from: date, date_to: date, bucket: str = "week") -> SeriesResponse:
        return build_series(self.dataset(), self._cfg, date_from, date_to, bucket)

    def get_policies(self) -> PoliciesResponse:
        items = [
            PolicyItem(
                id=preset_id,
                label=PRESET_LABELS.get(preset_id, preset_id),
                p_borrow_now=thresholds.p_borrow_now,
                p_wait=thresholds.p_wait,
                is_default=preset_id == self._cfg.money_default_preset,
            )
            for preset_id, thresholds in self._cfg.money_presets.items()
        ]
        return PoliciesResponse(
            policies=items,
            default={
                "p_borrow_now": self._cfg.money_p_borrow_now,
                "p_wait": self._cfg.money_p_wait,
            },
        )
