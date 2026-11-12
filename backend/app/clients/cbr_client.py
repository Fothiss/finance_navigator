"""Клиент Банка России: ключевая ставка, кривая ОФЗ, ставки по кредитам МСП."""

from __future__ import annotations

import time
from datetime import date, timedelta
from types import TracebackType

import httpx

from app.config.settings import Settings
from app.data.parsers import (
    build_key_rate_request,
    parse_key_rate_xml,
    parse_sme_rates_xlsx,
    parse_zcyc_html,
    pick_latest_bulletin_url,
)
from app.data.records import KeyRatePoint, OfzCurvePoint, SmeRatePoint
from app.errors import UpstreamUnavailableError

USER_AGENT = "finance-navigator/0.1 (+backend)"

# ЦБ возвращает пустую таблицу КБД на слишком длинный период: режем диапазон на окна.
OFZ_CHUNK_DAYS = 730


class CbrClient:
    """Тонкая обёртка над внешними выгрузками ЦБ с ретраями и валидацией."""

    def __init__(self, cfg: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._cfg = cfg
        self._client = httpx.Client(
            timeout=cfg.http_timeout_seconds,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    def __enter__(self) -> CbrClient:
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

    def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._cfg.http_retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)  # type: ignore[arg-type]
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:  # таймаут, 5xx, сетевая ошибка
                last_error = exc
                if attempt < self._cfg.http_retries:
                    time.sleep(0.05 * (attempt + 1))
        raise UpstreamUnavailableError(
            f"ЦБ недоступен: {url} ({type(last_error).__name__}: {last_error})"
        )

    def fetch_key_rate(self, date_from: date, date_to: date) -> list[KeyRatePoint]:
        """Ключевая ставка за период."""
        body, headers = build_key_rate_request(date_from, date_to)
        response = self._request("POST", self._cfg.cbr_soap_url, content=body, headers=headers)
        return parse_key_rate_xml(response.text)

    def fetch_ofz_curve(self, date_from: date, date_to: date) -> list[OfzCurvePoint]:
        """Кривая бескупонной доходности ОФЗ за период.

        ЦБ отдаёт пустую таблицу, если запросить слишком длинный период, поэтому
        диапазон режется на окна (см. `OFZ_CHUNK_DAYS`).
        """
        collected: dict[date, OfzCurvePoint] = {}
        chunk_start = date_from
        while chunk_start <= date_to:
            chunk_end = min(chunk_start + timedelta(days=OFZ_CHUNK_DAYS), date_to)
            response = self._request(
                "POST",
                self._cfg.cbr_zcyc_url,
                data={
                    "UniDbQuery.Posted": "True",
                    "UniDbQuery.From": chunk_start.strftime("%d.%m.%Y"),
                    "UniDbQuery.To": chunk_end.strftime("%d.%m.%Y"),
                },
            )
            for point in parse_zcyc_html(response.text):
                collected[point.date] = point
            chunk_start = chunk_end + timedelta(days=1)
        return sorted(collected.values(), key=lambda point: point.date)

    def fetch_sme_rates(self) -> list[SmeRatePoint]:
        """Помесячные ставки по кредитам МСП из последнего статистического бюллетеня."""
        page = self._request("GET", self._cfg.cbr_bulletin_page_url)
        url = pick_latest_bulletin_url(page.text, self._cfg.cbr_bulletin_page_url)
        response = self._request("GET", url)
        return parse_sme_rates_xlsx(response.content)
