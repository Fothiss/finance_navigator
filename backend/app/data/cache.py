"""Кеш внешних данных: TTL в памяти + JSON-снапшот на диске."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from cachetools import TTLCache
from pydantic import BaseModel

from app.config.settings import Settings

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


class SnapshotCache:
    """TTL-кеш в памяти с JSON-снапшотом.

    Снапшот нужен для офлайна и тестов: если загрузчик упал, отдаём последний
    сохранённый набор, а не ошибку. Снапшот при ошибке не удаляется.
    """

    def __init__(self, cfg: Settings, clock: Callable[[], float] = time.monotonic) -> None:
        self._dir = Path(cfg.cache_dir)
        self._clock = clock
        self._memory: TTLCache[str, list[BaseModel]] = TTLCache(
            maxsize=32, ttl=float(cfg.money_cache_ttl_seconds), timer=clock
        )

    def get_or_load(self, key: str, loader: Callable[[], list[M]], model: type[M]) -> list[M]:
        """Взять набор из памяти, иначе загрузить (с откатом на снапшот при ошибке)."""
        try:
            cached = self._memory[key]
        except KeyError:
            cached = None
        if cached is not None:
            return list(cached)  # type: ignore[arg-type]

        snapshot = self._read_snapshot(key, model)
        try:
            loaded = loader()
        except Exception:
            if snapshot is None:
                raise
            logger.warning("upstream load failed, serving snapshot %s", key)
            self._memory[key] = list(snapshot)
            return snapshot

        self._write_snapshot(key, loaded)
        self._memory[key] = list(loaded)
        return loaded

    def invalidate(self, key: str) -> None:
        """Сбросить значение в памяти (снапшот остаётся)."""
        self._memory.pop(key, None)

    def _snapshot_path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def _read_snapshot(self, key: str, model: type[M]) -> list[M] | None:
        path = self._snapshot_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [model.model_validate(item) for item in payload["data"]]
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("snapshot %s is unreadable, ignoring", key)
            return None

    def _write_snapshot(self, key: str, value: list[BaseModel]) -> None:
        payload = {
            "saved_at": datetime.now(UTC).isoformat(),
            "data": [item.model_dump(mode="json") for item in value],
        }
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._snapshot_path(key).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            logger.warning("cannot write snapshot %s", key)
