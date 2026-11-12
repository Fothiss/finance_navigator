"""Ручное обновление снапшотов: `python -m app.data.sync` из каталога backend."""

from __future__ import annotations

from app.clients.cbr_client import CbrClient
from app.clients.moex_client import MoexClient
from app.config.settings import settings
from app.data.cache import SnapshotCache
from app.data.sources import load_dataset


def main() -> None:
    """Скачать все источники модуля 1 и записать снапшоты."""
    cfg = settings
    cache = SnapshotCache(cfg)
    with CbrClient(cfg) as cbr, MoexClient(cfg) as moex:
        dataset = load_dataset(cache, cfg, cbr, moex)

    last_dates = dataset.last_dates()
    counts = {
        "cbr_key_rate": len(dataset.key_rate),
        "cbr_ofz_curve": len(dataset.ofz_curve),
        "moex_rusfar1m": len(dataset.rusfar),
        "cbr_sme_rates": len(dataset.sme_rates),
    }
    for name, last in last_dates.items():
        shown = last.isoformat() if last else "нет данных"
        print(f"{name:<16} точек={counts[name]:>5} последняя={shown}")


if __name__ == "__main__":
    main()
