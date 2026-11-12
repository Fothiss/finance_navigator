"""Тесты эндпоинта `/api/v1/money/signals`."""

from __future__ import annotations

from datetime import date

from tests.synthetic import SyntheticSpec, make_dataset

TODAY = date(2026, 1, 2)


def test_signals_returns_two_variants(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/signals")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert len(body["signals"]) == 2
    variants = {signal["variant"] for signal in body["signals"]}
    assert variants == {"rusfar_term_premium", "ofz_curve_premium"}
    assert body["target"]["horizon_days"] == 30
    assert body["comparison"]["metric"] == "brier"
    assert body["comparison"]["leader"] in variants
    assert body["benchmark"] is not None
    assert body["data"]["stale"] is False


def test_signal_contains_probability_with_interval(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    body = client.get("/api/v1/money/signals").json()

    for signal in body["signals"]:
        assert signal["status"] == "ok"
        probability = signal["probability"]
        low, high = probability["interval_80"]
        assert low <= probability["value"] <= high
        assert 0.0 <= probability["baseline"]["value"] <= 1.0
        assert (
            abs(probability["lift"] - (probability["value"] - probability["baseline"]["value"]))
            < 1e-3
        )
        assert probability["n_observations"] > 0
        assert signal["evidence"]["status"] == "passed"
        assert signal["headline"]
        assert signal["drivers"]


def test_policy_from_query(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    body = client.get("/api/v1/money/signals", params={"p_borrow_now": 0.70, "p_wait": 0.45}).json()

    assert body["policy"]["source"] == "user"
    assert body["policy"]["p_borrow_now"] == 0.70
    assert body["policy"]["p_wait"] == 0.45
    assert body["policy"]["recommended_verdict"] is not None


def test_policy_default(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    body = client.get("/api/v1/money/signals").json()
    assert body["policy"]["source"] == "default"
    assert body["policy"]["default"]["p_borrow_now"] > 0


def test_preset_changes_source(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    body = client.get("/api/v1/money/signals", params={"preset": "careful"}).json()
    assert body["policy"]["source"] == "preset:careful"


def test_unknown_preset_rejected(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/signals", params={"preset": "unknown"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "unknown" in response.json()["detail"]


def test_invalid_thresholds_rejected(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/signals", params={"p_borrow_now": 0.4, "p_wait": 0.6})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


def test_model_parameters_are_forbidden(api_factory) -> None:
    client = api_factory(make_dataset(), TODAY)
    response = client.get("/api/v1/money/signals", params={"z_threshold": 5})
    assert response.status_code == 422
    assert "z_threshold" in response.json()["detail"]


def test_insufficient_evidence_on_short_history(api_factory) -> None:
    short = SyntheticSpec(months=18, start=date(2024, 7, 1))
    client = api_factory(make_dataset(short), TODAY)
    body = client.get("/api/v1/money/signals").json()

    assert body["status"] == "insufficient_evidence"
    for signal in body["signals"]:
        assert signal["status"] == "insufficient_evidence"
        assert signal["verdict"] is None
        assert signal["probability"] is None


def test_stale_data_blocks_verdict(api_factory) -> None:
    dataset = make_dataset(SyntheticSpec(last_day=date(2021, 12, 31)))
    client = api_factory(dataset, TODAY)
    body = client.get("/api/v1/money/signals").json()

    assert body["data"]["stale"] is True
    assert body["status"] == "stale_data"
    for signal in body["signals"]:
        assert signal["status"] == "stale_data"
        assert signal["verdict"] is None
        assert signal["probability"] is None
