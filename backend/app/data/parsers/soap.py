"""Разбор SOAP-ответов `DailyInfo.asmx`."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

from app.data.records import KeyRatePoint

CBR_NS = "http://web.cbr.ru"


def _local(tag: str) -> str:
    """Локальное имя тега без namespace."""
    return tag.rsplit("}", 1)[-1]


def build_key_rate_request(date_from: date, date_to: date) -> tuple[str, dict[str, str]]:
    """Тело и заголовки SOAP-запроса `KeyRateXML`.

    Параметры называются `fromDate` (нижняя `f`) и `ToDate`: при другой раскладке
    сервис не отвечает ошибкой, а возвращает пустой результат.
    """
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Body><KeyRateXML xmlns="{CBR_NS}/">'
        f"<fromDate>{date_from.isoformat()}T00:00:00</fromDate>"
        f"<ToDate>{date_to.isoformat()}T00:00:00</ToDate>"
        "</KeyRateXML></soap:Body></soap:Envelope>"
    )
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{CBR_NS}/KeyRateXML"',
    }
    return body, headers


def parse_key_rate_xml(payload: str) -> list[KeyRatePoint]:
    """Разобрать ответ `KeyRateXML` в список точек, отсортированный по дате."""
    root = ET.fromstring(payload)

    for el in root.iter():
        if _local(el.tag) == "Error" and (el.text or "").strip():
            raise ValueError(f"DailyInfo вернул ошибку: {el.text}")

    points: list[KeyRatePoint] = []
    for el in root.iter():
        if _local(el.tag) != "KR":
            continue
        raw_date: str | None = None
        raw_rate: str | None = None
        for child in el:
            name = _local(child.tag)
            if name == "DT":
                raw_date = (child.text or "").strip()
            elif name == "Rate":
                raw_rate = (child.text or "").strip()
        if not raw_date or not raw_rate:
            continue
        points.append(
            KeyRatePoint(
                date=date.fromisoformat(raw_date[:10]),
                rate=float(raw_rate.replace(",", ".")),
            )
        )
    return sorted(points, key=lambda point: point.date)
