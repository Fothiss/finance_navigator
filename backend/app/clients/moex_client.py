"""Клиент MOEX ISS: премия денежного рынка RUSFAR1M."""

from __future__ import annotations

import time
from datetime import date
from types import TracebackType

import httpx

from app.config.settings import Settings
from app.data.parsers.iss import parse_rusfar_page
from app.data.records import RusfarPoint
from app.errors import UpstreamUnavailableError

USER_AGENT = "finance-navigator/0.1 (+backend)"
PAGE_SIZE = 100


class MoexClient:
    """История RUSFAR1M с пагинацией по 100 строк."""

    def __init__(self, cfg: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._cfg = cfg
        self._client = httpx.Client(
            timeout=cfg.http_timeout_seconds,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    def __enter__(self) -> MoexClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, url: str, params: dict[str, str | int]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._cfg.http_retries + 1):
            try:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._cfg.http_retries:
                    time.sleep(0.05 * (attempt + 1))
        raise UpstreamUnavailableError(
            f"MOEX недоступен: {url} ({type(last_error).__name__}: {last_error})"
        )

    def fetch_rusfar1m(self, date_from: date, date_to: date) -> list[RusfarPoint]:
        """Дневная история RUSFAR1M за период (с пагинацией и дедупликацией)."""
        collected: dict[date, RusfarPoint] = {}
        start = 0
        while True:
            response = self._request(
                self._cfg.moex_rusfar_url,
                {
                    "from": date_from.isoformat(),
                    "till": date_to.isoformat(),
                    "start": start,
                    "iss.meta": "off",
                    "history.columns": "TRADEDATE,CLOSE",
                },
            )
            page = parse_rusfar_page(response.text)
            for point in page:
                collected[point.date] = point
            if len(page) < PAGE_SIZE:
                break
            start += len(page)
        return sorted(collected.values(), key=lambda point: point.date)
