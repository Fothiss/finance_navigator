"""Разбор ответов MOEX ISS."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.data.records import RusfarPoint


def parse_rusfar_page(payload: str | bytes | dict[str, Any]) -> list[RusfarPoint]:
    """Разобрать одну страницу истории RUSFAR1M (колонки TRADEDATE, CLOSE)."""
    data = json.loads(payload) if isinstance(payload, str | bytes) else payload
    history = data.get("history", {})
    columns = history.get("columns", [])
    if "TRADEDATE" not in columns or "CLOSE" not in columns:
        return []
    i_date = columns.index("TRADEDATE")
    i_close = columns.index("CLOSE")

    points: list[RusfarPoint] = []
    for row in history.get("data", []):
        if len(row) <= max(i_date, i_close):
            continue
        raw_close = row[i_close]
        if raw_close is None:
            continue
        points.append(
            RusfarPoint(date=date.fromisoformat(str(row[i_date])[:10]), rate=float(raw_close))
        )
    return points
