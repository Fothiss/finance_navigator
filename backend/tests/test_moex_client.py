"""Тесты клиента MOEX ISS на подменённом транспорте."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.clients.moex_client import MoexClient
from app.config.settings import Settings
from app.errors import UpstreamUnavailableError
from tests.conftest import read_fixture


def test_fetch_rusfar1m_parses_history(cfg: Settings) -> None:
    body = read_fixture("moex", "rusfar1m_2026_11.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["history.columns"] == "TRADEDATE,CLOSE"
        return httpx.Response(200, content=body)

    with MoexClient(cfg, transport=httpx.MockTransport(handler)) as client:
        points = client.fetch_rusfar1m(date(2026, 11, 1), date(2026, 11, 12))
    assert points
    assert points[-1].date == date(2026, 11, 11)
    assert points[-1].rate == pytest.approx(14.01, abs=0.01)


def test_fetch_rusfar1m_paginates(cfg: Settings) -> None:
    # 150 строк истории: первая страница полная (100), вторая — остаток.
    rows = [
        [f"2026-{month:02d}-{day:02d}", 10.0]
        for month in (1, 2, 3, 4, 5, 6)
        for day in range(1, 26)
    ]
    pages = [
        {"history": {"columns": ["TRADEDATE", "CLOSE"], "data": rows[:100]}},
        {"history": {"columns": ["TRADEDATE", "CLOSE"], "data": rows[100:]}},
    ]

    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(int(request.url.params.get("start", 0)))
        return httpx.Response(200, json=pages[len(calls) - 1])

    with MoexClient(cfg, transport=httpx.MockTransport(handler)) as client:
        points = client.fetch_rusfar1m(date(2026, 1, 1), date(2026, 6, 30))
    assert len(points) == 150
    assert calls == [0, 100]


@pytest.mark.parametrize("status_code", [404, 429, 500])
def test_fetch_rusfar1m_returns_upstream_error(cfg: Settings, status_code: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "nope"})

    with (
        MoexClient(cfg, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(UpstreamUnavailableError),
    ):
        client.fetch_rusfar1m(date(2026, 11, 1), date(2026, 11, 12))
