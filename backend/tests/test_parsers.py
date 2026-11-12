"""Тесты разбора внешних ответов на сохранённых фикстурах."""

from __future__ import annotations

import pytest

from app.data.parsers import (
    parse_key_rate_xml,
    parse_rusfar_page,
    parse_sme_rates_xlsx,
    parse_zcyc_html,
    pick_latest_bulletin_url,
)
from tests.conftest import read_fixture, read_text_fixture


def test_parse_key_rate_xml_sorted_and_valid() -> None:
    points = parse_key_rate_xml(read_text_fixture("cbr", "key_rate_2026.xml"))
    assert points
    assert points == sorted(points, key=lambda point: point.date)
    assert all(0 < point.rate < 100 for point in points)
    assert points[-1].rate == 14.0


def test_parse_key_rate_xml_detects_error_payload() -> None:
    payload = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><KeyRateXMLResponse xmlns="http://web.cbr.ru/">'
        '<KeyRateXMLResult><KeyRate xmlns=""><Error>bad request</Error></KeyRate>'
        "</KeyRateXMLResult></KeyRateXMLResponse></soap:Body></soap:Envelope>"
    )
    with pytest.raises(ValueError):
        parse_key_rate_xml(payload)


def test_parse_key_rate_xml_empty_when_no_rows() -> None:
    payload = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><KeyRateXMLResponse xmlns="http://web.cbr.ru/">'
        '<KeyRateXMLResult><KeyRate xmlns="" /></KeyRateXMLResult>'
        "</KeyRateXMLResponse></soap:Body></soap:Envelope>"
    )
    assert parse_key_rate_xml(payload) == []


def test_parse_zcyc_html_curve_has_one_year_tenor() -> None:
    points = parse_zcyc_html(read_text_fixture("cbr", "zcyc_2026_11.html"))
    assert points
    assert points == sorted(points, key=lambda point: point.date)
    latest = points[-1]
    assert latest.tenor(1.0) == pytest.approx(14.00, abs=0.01)
    assert latest.tenor(0.25) is not None
    assert len(latest.curve) >= 12


def test_parse_rusfar_page_from_fixture() -> None:
    points = parse_rusfar_page(read_fixture("moex", "rusfar1m_2026_11.json"))
    assert points
    assert points == sorted(points, key=lambda point: point.date)
    assert points[-1].rate == pytest.approx(14.01, abs=0.01)


def test_parse_rusfar_page_without_expected_columns_returns_empty() -> None:
    assert parse_rusfar_page('{"history": {"columns": ["TRADEDATE"], "data": []}}') == []


def test_parse_sme_rates_xlsx_monthly_series() -> None:
    points = parse_sme_rates_xlsx(read_fixture("cbr", "bulletin_lending.xlsx"))
    assert len(points) >= 30
    assert points[0].month == "2024-01"
    assert points == sorted(points, key=lambda point: point.month)
    assert all(0 < point.rate < 100 for point in points)
    assert points[-1].month > "2025-06"


def test_pick_latest_bulletin_url_prefers_newest_month() -> None:
    html = (
        '<a href="/Collection/File/1/stat_bulletin_lending_24-01_45.xlsx">a</a>'
        '<a href="/Collection/File/2/stat_bulletin_lending_26-08_75.xlsx">b</a>'
        '<a href="/Collection/File/3/stat_bulletin_lending_25-03_55.xlsx">c</a>'
    )
    url = pick_latest_bulletin_url(html, "https://www.cbr.ru/statistics/bank_sector/sors/")
    assert url.endswith("stat_bulletin_lending_26-08_75.xlsx")
    assert url.startswith("https://www.cbr.ru/")


def test_pick_latest_bulletin_url_raises_without_links() -> None:
    with pytest.raises(ValueError):
        pick_latest_bulletin_url("<html></html>", "https://www.cbr.ru/")
