"""Тесты клиента ЦБ на подменённом транспорте httpx."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.clients.cbr_client import CbrClient
from app.config.settings import Settings
from app.errors import UpstreamUnavailableError
from tests.conftest import read_fixture, read_text_fixture


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def test_fetch_key_rate_parses_soap(cfg: Settings) -> None:
    body = read_text_fixture("cbr", "key_rate_2026.xml")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert b"KeyRateXML" in request.content
        return httpx.Response(200, text=body)

    with CbrClient(cfg, transport=_transport(handler)) as client:
        points = client.fetch_key_rate(date(2026, 1, 1), date(2026, 2, 1))
    assert points
    assert points[-1].rate == 14.0


def test_fetch_key_rate_raises_on_broken_xml(cfg: Settings) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<not-xml")

    with (
        CbrClient(cfg, transport=_transport(handler)) as client,
        pytest.raises(Exception),  # noqa: B017 - ожидаем ошибку разбора
    ):
        client.fetch_key_rate(date(2026, 1, 1), date(2026, 2, 1))


def test_fetch_key_rate_raises_upstream_error_on_timeout(cfg: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    with (
        CbrClient(cfg, transport=_transport(handler)) as client,
        pytest.raises(UpstreamUnavailableError),
    ):
        client.fetch_key_rate(date(2026, 1, 1), date(2026, 2, 1))


def test_fetch_ofz_curve_posts_unidbquery(cfg: Settings) -> None:
    body = read_text_fixture("cbr", "zcyc_2026_11.html")
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["content"] = request.content.decode()
        return httpx.Response(200, text=body)

    with CbrClient(cfg, transport=_transport(handler)) as client:
        points = client.fetch_ofz_curve(date(2026, 11, 1), date(2026, 11, 12))
    assert "UniDbQuery.Posted=True" in seen["content"]
    assert points
    assert points[-1].tenor(1.0) == pytest.approx(14.0, abs=0.01)


def test_fetch_ofz_curve_splits_long_range_into_chunks(cfg: Settings) -> None:
    body = read_text_fixture("cbr", "zcyc_2026_11.html")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.content.decode())
        return httpx.Response(200, text=body)

    with CbrClient(cfg, transport=_transport(handler)) as client:
        client.fetch_ofz_curve(date(2016, 1, 1), date(2026, 1, 1))
    assert len(calls) > 1
    assert all("UniDbQuery.From" in body for body in calls)


def test_fetch_sme_rates_follows_bulletin_link(cfg: Settings) -> None:
    page = (
        "<html><body>"
        '<a href="/Collection/File/1/stat_bulletin_lending_26-08_75.xlsx">x</a>'
        "</body></html>"
    )
    xlsx = read_fixture("cbr", "bulletin_lending.xlsx")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".xlsx"):
            return httpx.Response(200, content=xlsx)
        return httpx.Response(200, text=page)

    with CbrClient(cfg, transport=_transport(handler)) as client:
        points = client.fetch_sme_rates()
    assert points
    assert points[0].month == "2024-01"
