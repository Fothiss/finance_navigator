"""Тесты эндпоинта `/api/v1/money/series`."""

from __future__ import annotations

from datetime import date

from tests.synthetic import make_dataset

TODAY = date(2026, 1, 2)
RANGE = {"from": "2024-01-01", "to": "2025-12-31"}


def test_series_returns_spreads_and_rates(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={**RANGE, "bucket": "week"})
    assert response.status_code == 200

    body = response.json()
    assert len(body["spreads"]) == 2
    variants = {row["variant"] for row in body["spreads"]}
    assert variants == {"rusfar_term_premium", "ofz_curve_premium"}
    for row in body["spreads"]:
        assert row["points"]
        assert "date" in row["points"][0]
        assert "premium_bp" in row["points"][0]
    assert body["rates"]
    assert "month" in body["rates"][0]
    assert "sme_rate" in body["rates"][0]
    assert body["meta"]["spread_last_date"]
    assert body["meta"]["rates_last_month"]


def test_bucket_changes_only_daily_groups(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    day_body = client.get("/api/v1/money/series", params={**RANGE, "bucket": "day"}).json()
    month_body = client.get("/api/v1/money/series", params={**RANGE, "bucket": "month"}).json()

    day_points = len(day_body["spreads"][0]["points"])
    month_points = len(month_body["spreads"][0]["points"])
    assert month_points < day_points
    assert day_body["rates"] == month_body["rates"]


def test_series_rejects_reversed_range(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={"from": "2026-01-01", "to": "2024-01-01"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


def test_series_rejects_future_to(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={"from": "2024-01-01", "to": "2027-01-01"})
    assert response.status_code == 422


def test_series_rejects_too_long_range(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={"from": "2010-01-01", "to": "2026-01-01"})
    assert response.status_code == 422


def test_series_rejects_unknown_bucket(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={**RANGE, "bucket": "hour"})
    assert response.status_code == 422
    assert "bucket" in response.json()["detail"]


def test_series_rejects_unknown_parameter(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/series", params={**RANGE, "z_window": 10})
    assert response.status_code == 422
    assert "z_window" in response.json()["detail"]
