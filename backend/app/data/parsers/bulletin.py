"""Разбор статистического бюллетеня ЦБ по кредитованию (ставки МСП)."""

from __future__ import annotations

import io
import re
from urllib.parse import urljoin

from openpyxl import load_workbook

from app.data.records import SmeRatePoint

SME_SHEET = "Таблица 5"
BULLETIN_LINK_RE = re.compile(r'href="([^"]*lending[^"]*\.xlsx)"', re.I)
MONTH_RE = re.compile(r"(?P<name>[А-Яа-яЁё]+)\s+(?P<year>\d{4})")

MONTHS: dict[str, int] = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
}


def pick_latest_bulletin_url(page_html: str, base_url: str) -> str:
    """Ссылка на самый свежий бюллетень: имена файлов содержат ГГ-ММ."""
    links = sorted(
        {urljoin(base_url, raw) for raw in BULLETIN_LINK_RE.findall(page_html)},
        key=lambda url: url.rsplit("/", 1)[-1],
    )
    if not links:
        raise ValueError("на странице статистики не найдено ни одного бюллетеня по кредитованию")
    return links[-1]


def parse_month_label(label: str) -> str | None:
    """'Январь 2024 г.' -> '2024-01'."""
    match = MONTH_RE.search(label)
    if match is None:
        return None
    month = MONTHS.get(match.group("name").lower())
    if month is None:
        return None
    return f"{int(match.group('year')):04d}-{month:02d}"


def parse_sme_rates_xlsx(content: bytes) -> list[SmeRatePoint]:
    """Разобрать «Таблицу 5» бюллетеня в помесячный ряд ставок МСП.

    Колонки листа: месяц | доля до 1 года | доля свыше 1 года |
    ставка до 1 года | ставка свыше 1 года | темп прироста | темп прироста.
    """
    workbook = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    if SME_SHEET not in workbook.sheetnames:
        raise ValueError(f"в бюллетене нет листа {SME_SHEET!r}")

    sheet = workbook[SME_SHEET]
    points: list[SmeRatePoint] = []
    for row in sheet.iter_rows(min_row=5, max_col=5, values_only=True):
        if not row or row[0] is None:
            continue
        month = parse_month_label(str(row[0]))
        if month is None:
            continue
        rate_upto_1y, rate_over_1y = row[3], row[4]
        if not isinstance(rate_upto_1y, int | float) or not isinstance(rate_over_1y, int | float):
            continue
        points.append(
            SmeRatePoint(
                month=month,
                rate_upto_1y=float(rate_upto_1y),
                rate_over_1y=float(rate_over_1y),
            )
        )
    if not points:
        raise ValueError("в «Таблице 5» не найдено ни одной строки с месячными ставками")
    return sorted(points, key=lambda point: point.month)
