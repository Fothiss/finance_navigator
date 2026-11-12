"""Тесты эндпоинта `/api/v1/money/policies`."""

from __future__ import annotations

from datetime import date

from app.config.settings import Settings
from tests.synthetic import make_dataset

TODAY = date(2026, 1, 2)


def test_policies_list(api_factory, cfg: Settings) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/policies")
    assert response.status_code == 200

    body = response.json()
    assert body["policies"]
    assert sum(1 for item in body["policies"] if item["is_default"]) == 1
    for item in body["policies"]:
        assert 0.0 <= item["p_wait"] < item["p_borrow_now"] <= 1.0
        assert item["label"]
    assert body["default"]["p_borrow_now"] == cfg.money_p_borrow_now
    assert body["default"]["p_wait"] == cfg.money_p_wait


def test_policies_match_settings(api_factory, cfg: Settings) -> None:
    client = api_factory(make_dataset(), TODAY)
    body = client.get("/api/v1/money/policies").json()
    by_id = {item["id"]: item for item in body["policies"]}
    assert set(by_id) == set(cfg.money_presets)
    for preset_id, thresholds in cfg.money_presets.items():
        assert by_id[preset_id]["p_borrow_now"] == thresholds.p_borrow_now
        assert by_id[preset_id]["p_wait"] == thresholds.p_wait
    assert by_id[cfg.money_default_preset]["is_default"] is True
