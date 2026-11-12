"""Разбор HTML-таблицы кривой бескупонной доходности ОФЗ (КБД)."""

from __future__ import annotations

import re
from datetime import datetime

from app.data.records import OfzCurvePoint

DEFAULT_TENORS: tuple[float, ...] = (
    0.25,
    0.5,
    0.75,
    1.0,
    2.0,
    3.0,
    5.0,
    7.0,
    10.0,
    15.0,
    20.0,
    30.0,
)

_DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S | re.I)
_CELL_RE = re.compile(r"<t[dh][^>]*>.*?</t[dh]>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")


def _to_float(cell: str) -> float | None:
    text = _TAG_RE.sub("", cell).replace("\xa0", " ").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _cells(row: str) -> list[str]:
    return [_TAG_RE.sub("", cell).replace("\xa0", " ").strip() for cell in _CELL_RE.findall(row)]


def _find_tenors(rows: list[list[str]]) -> tuple[float, ...]:
    """Найти строку заголовка с тенорами (0,25 / 0,5 / … / 30)."""
    for cells in rows:
        values: list[float] = []
        for cell in cells:
            number = _to_float(cell)
            if number is None or not 0 < number <= 100:
                values = []
                break
            values.append(number)
        if len(values) >= 3:
            return tuple(values)
    return DEFAULT_TENORS


def parse_zcyc_html(payload: str) -> list[OfzCurvePoint]:
    """Разобрать таблицу КБД в список точек, отсортированный по дате.

    Значения сопоставляются с тенором по позиции из строки заголовка, потому что
    в части исторических периодов число колонок меньше числа теноров.
    """
    rows = [_cells(row) for row in _ROW_RE.findall(payload)]
    tenors = _find_tenors(rows)

    points: list[OfzCurvePoint] = []
    for cells in rows:
        if not cells:
            continue
        match = _DATE_RE.match(cells[0])
        if match is None:
            continue
        day, month, year = (int(part) for part in match.groups())
        values: list[float] = []
        for cell in cells[1:]:
            number = _to_float(cell)
            if number is None:
                break
            values.append(number)
        if not values:
            continue
        curve = dict(zip(tenors[: len(values)], values, strict=False))
        points.append(OfzCurvePoint(date=datetime(year, month, day).date(), curve=curve))
    return sorted(points, key=lambda point: point.date)
