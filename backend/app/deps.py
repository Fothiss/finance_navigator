"""Зависимости FastAPI: единственный экземпляр сервисов и клиентов."""

from __future__ import annotations

from app.clients.cbr_client import CbrClient
from app.clients.moex_client import MoexClient
from app.config.settings import settings
from app.data.cache import SnapshotCache
from app.services.money.service import MoneyService

_service: MoneyService | None = None


def get_money_service() -> MoneyService:
    """Ленивая инициализация сервиса модуля 1."""
    global _service
    if _service is None:
        _service = MoneyService(
            cfg=settings,
            cache=SnapshotCache(settings),
            cbr=CbrClient(settings),
            moex=MoexClient(settings),
        )
    return _service


def reset_money_service(service: MoneyService | None = None) -> None:
    """Подменить сервис (для тестов)."""
    global _service
    _service = service
