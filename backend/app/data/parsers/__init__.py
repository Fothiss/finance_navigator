"""Разбор ответов Банка России и MOEX."""

from __future__ import annotations

from app.data.parsers.bulletin import parse_sme_rates_xlsx, pick_latest_bulletin_url
from app.data.parsers.iss import parse_rusfar_page
from app.data.parsers.soap import build_key_rate_request, parse_key_rate_xml
from app.data.parsers.zcyc import DEFAULT_TENORS, parse_zcyc_html

__all__ = [
    "DEFAULT_TENORS",
    "build_key_rate_request",
    "parse_key_rate_xml",
    "parse_rusfar_page",
    "parse_sme_rates_xlsx",
    "parse_zcyc_html",
    "pick_latest_bulletin_url",
]
