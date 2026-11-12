"""Тесты кеша: TTL, снапшот, поведение при ошибке загрузчика."""

from __future__ import annotations

from datetime import date

import pytest

from app.config.settings import Settings
from app.data.cache import SnapshotCache
from app.data.records import KeyRatePoint


class Clock:
    """Управляемые часы для проверки TTL."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _points(rate: float = 16.0) -> list[KeyRatePoint]:
    return [KeyRatePoint(date=date(2026, 11, 11), rate=rate)]


def test_two_calls_within_ttl_load_once(cfg: Settings) -> None:
    calls: list[int] = []
    cache = SnapshotCache(cfg, clock=Clock())

    def loader() -> list[KeyRatePoint]:
        calls.append(1)
        return _points()

    first = cache.get_or_load("k", loader, KeyRatePoint)
    second = cache.get_or_load("k", loader, KeyRatePoint)
    assert len(calls) == 1
    assert first == second


def test_ttl_expiry_triggers_reload(cfg: Settings) -> None:
    clock = Clock()
    calls: list[int] = []
    cache = SnapshotCache(cfg, clock=clock)

    def loader() -> list[KeyRatePoint]:
        calls.append(1)
        return _points(rate=10.0 + len(calls))

    cache.get_or_load("k", loader, KeyRatePoint)
    clock.now = cfg.money_cache_ttl_seconds + 1
    second = cache.get_or_load("k", loader, KeyRatePoint)
    assert len(calls) == 2
    assert second[0].rate == 12.0


def test_failed_load_keeps_snapshot(cfg: Settings) -> None:
    clock = Clock()
    cache = SnapshotCache(cfg, clock=clock)
    cache.get_or_load("k", _points, KeyRatePoint)
    snapshot_path = cfg.cache_dir / "k.json"
    assert snapshot_path.exists()

    clock.now = cfg.money_cache_ttl_seconds + 1

    def broken() -> list[KeyRatePoint]:
        raise RuntimeError("upstream down")

    restored = cache.get_or_load("k", broken, KeyRatePoint)
    assert restored[0].rate == 16.0
    assert snapshot_path.exists()


def test_failed_load_without_snapshot_raises(cfg: Settings) -> None:
    cache = SnapshotCache(cfg, clock=Clock())

    def broken() -> list[KeyRatePoint]:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError):
        cache.get_or_load("missing", broken, KeyRatePoint)


def test_corrupted_snapshot_is_ignored(cfg: Settings) -> None:
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    (cfg.cache_dir / "k.json").write_text("{not json", encoding="utf-8")
    cache = SnapshotCache(cfg, clock=Clock())
    assert cache.get_or_load("k", _points, KeyRatePoint)[0].rate == 16.0
