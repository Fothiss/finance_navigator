"""Unit-тесты сервисов: индикаторы, таргет, правило, бэктест, политика."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.config.settings import Settings
from app.services.money.backtest import BacktestStatus, compare_variants, run_backtest
from app.services.money.benchmark import build_benchmark
from app.services.money.indicators import (
    RUSFAR,
    VARIANTS,
    build_premium_series,
    key_rate_at_horizon,
    z_scores,
)
from app.services.money.policy import Policy, Verdict, decide, resolve_policy
from app.services.money.rule import estimate_rule, wilson_interval
from app.services.money.target import build_monthly_observations
from tests.synthetic import SyntheticSpec, make_dataset


def test_premium_series_has_both_variants(cfg: Settings) -> None:
    dataset = make_dataset()
    premiums = build_premium_series(dataset, cfg)
    assert set(premiums) == set(VARIANTS)
    for variant in VARIANTS:
        assert premiums[variant]
        assert premiums[variant][-1].date >= premiums[variant][0].date
    # премия RUSFAR считается как (ставка − ключевая) * 100
    first = premiums[RUSFAR][-1]
    assert first.premium_bp in {200.0, -50.0}


def test_z_scores_are_causal(cfg: Settings) -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]
    scores = z_scores(values, window=4)
    assert scores[0] is None
    # первые точки окна не имеют достаточной выборки
    assert all(score is None or isinstance(score, float) for score in scores)
    # выброс в конце не влияет на предыдущие значения
    assert scores[3] == z_scores(values[:4], window=4)[3]


def test_key_rate_at_horizon_requires_future_data() -> None:
    dates = [date(2026, 1, 1), date(2026, 1, 20)]
    rates = [10.0, 11.0]
    assert key_rate_at_horizon(dates, rates, date(2026, 1, 1), 30) is None
    assert key_rate_at_horizon(dates, rates, date(2026, 1, 1), 10) == 10.0


def test_monthly_observations_target_follows_synthetic_pattern(cfg: Settings) -> None:
    dataset = make_dataset()
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    assert len(observations) > 30
    with_target = [row for row in observations if row.target_up is not None]
    assert with_target
    ups = [row for row in with_target if row.target_up]
    assert ups and len(ups) < len(with_target)


def test_estimate_rule_separates_regimes(cfg: Settings) -> None:
    dataset = make_dataset()
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    estimate = estimate_rule(observations, RUSFAR, cfg)
    assert estimate is not None
    assert estimate.regime.probability is not None
    assert estimate.calm.probability is not None
    assert estimate.regime.probability > estimate.baseline
    assert estimate.calm.probability < estimate.baseline


def test_backtest_passes_on_synthetic_signal(cfg: Settings) -> None:
    dataset = make_dataset()
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    for variant in VARIANTS:
        estimate = estimate_rule(observations, variant, cfg)
        assert estimate is not None
        test = run_backtest(observations, variant, estimate, cfg)
        assert test.status == BacktestStatus.passed
        assert test.brier is not None
        assert test.hit_rate is not None
        assert test.n_observations > cfg.money_min_observations


def test_backtest_fails_with_short_history(cfg: Settings) -> None:
    dataset = make_dataset(SyntheticSpec(months=18))
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    estimate = estimate_rule(observations, RUSFAR, cfg)
    assert estimate is not None
    test = run_backtest(observations, RUSFAR, estimate, cfg)
    assert test.status == BacktestStatus.failed
    assert test.reason is not None


def test_backtest_not_run_without_targets(cfg: Settings) -> None:
    dataset = make_dataset(SyntheticSpec(months=8))
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    estimate = estimate_rule(observations, RUSFAR, cfg)
    if estimate is None:
        return  # данных совсем мало — правило не строится
    test = run_backtest(observations, RUSFAR, estimate, cfg)
    assert test.status in {BacktestStatus.failed, BacktestStatus.not_run}


def test_wilson_interval_edges() -> None:
    low, high = wilson_interval(0, 0)
    assert (low, high) == (0.0, 1.0)
    low, high = wilson_interval(5, 10)
    assert low < 0.5 < high
    low_all, high_all = wilson_interval(10, 10)
    assert low_all > 0.5 and high_all <= 1.0


def test_compare_variants_reports_leader(cfg: Settings) -> None:
    dataset = make_dataset()
    premiums = build_premium_series(dataset, cfg)
    observations = build_monthly_observations(dataset.key_rate, premiums, cfg)
    tests = {}
    for variant in VARIANTS:
        estimate = estimate_rule(observations, variant, cfg)
        assert estimate is not None
        tests[variant] = run_backtest(observations, variant, estimate, cfg)
    comparison = compare_variants(tests, cfg)
    assert comparison.metric == "brier"
    assert comparison.leader in set(VARIANTS)
    assert comparison.verdict in {"stable", "inconclusive"}
    assert set(comparison.by_variant) == set(VARIANTS)


def test_benchmark_premium_from_synthetic(cfg: Settings) -> None:
    dataset = make_dataset()
    benchmark = build_benchmark(dataset.key_rate, dataset.sme_rates)
    assert benchmark is not None
    assert benchmark.premium_bp == pytest.approx(300.0, abs=1.0)


def test_policy_resolution_order(cfg: Settings) -> None:
    default = resolve_policy(cfg)
    assert default.source == "default"
    assert default.p_borrow_now == cfg.money_p_borrow_now

    preset = resolve_policy(cfg, preset="careful")
    assert preset.source == "preset:careful"
    assert preset.p_borrow_now == cfg.money_presets["careful"].p_borrow_now

    user = resolve_policy(cfg, p_borrow_now=0.7, p_wait=0.45)
    assert user.source == "user"
    assert user.p_borrow_now == 0.7


def test_policy_rejects_invalid_thresholds(cfg: Settings) -> None:
    with pytest.raises(ValueError):
        resolve_policy(cfg, p_borrow_now=0.4, p_wait=0.5)
    with pytest.raises(KeyError):
        resolve_policy(cfg, preset="unknown")
    with pytest.raises(ValueError):
        resolve_policy(cfg, p_borrow_now=0.5)


def test_decide_boundaries(cfg: Settings) -> None:
    policy = Policy(source="user", p_borrow_now=0.65, p_wait=0.45)
    assert decide(0.65, policy) == Verdict.borrow_now
    assert decide(0.64, policy) == Verdict.watch
    assert decide(0.45, policy) == Verdict.watch
    assert decide(0.44, policy) == Verdict.wait
    assert decide(None, policy) is None


def test_target_has_no_lookahead(cfg: Settings) -> None:
    dataset = make_dataset()
    cutoff = dataset.key_rate[len(dataset.key_rate) // 2].date
    truncated = make_dataset(SyntheticSpec(last_day=cutoff))

    full_points = build_premium_series(dataset, cfg)[RUSFAR]
    cut_points = build_premium_series(truncated, cfg)[RUSFAR]
    cut_by_date = {point.date: point for point in cut_points}
    for point in full_points:
        if point.date > cutoff:
            continue
        assert point.date in cut_by_date
        assert cut_by_date[point.date].premium_bp == point.premium_bp

    full_obs = build_monthly_observations(dataset.key_rate, build_premium_series(dataset, cfg), cfg)
    cut_obs = build_monthly_observations(
        truncated.key_rate, build_premium_series(truncated, cfg), cfg
    )
    cut_targets = {row.date: row.target_up for row in cut_obs}
    for row in full_obs:
        if row.date > cutoff - timedelta(days=30):
            continue
        if row.date in cut_targets:
            assert cut_targets[row.date] == row.target_up
