"""Схемы API модуля 1. Источник типов для OpenAPI и фронтенда."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.money.backtest import BacktestStatus
from app.services.money.policy import Verdict


class SignalStatus(StrEnum):
    ok = "ok"
    insufficient_evidence = "insufficient_evidence"
    stale_data = "stale_data"


class Target(BaseModel):
    """Событие, вероятность которого оценивается."""

    event: str
    horizon_days: int


class ModelInfo(BaseModel):
    name: str
    kind: str = "rule"


class BaselineInfo(BaseModel):
    name: str
    value: float


class ProbabilityBlock(BaseModel):
    """Вероятность события с интервалом и baseline."""

    event: str
    horizon_days: int
    value: float = Field(ge=0.0, le=1.0)
    interval_80: tuple[float, float]
    model: ModelInfo
    baseline: BaselineInfo
    lift: float
    n_observations: int
    threshold_z: float

    @model_validator(mode="after")
    def _interval_covers_value(self) -> ProbabilityBlock:
        low, high = self.interval_80
        if low > high:
            raise ValueError("нижняя граница интервала больше верхней")
        if not low - 1e-9 <= self.value <= high + 1e-9:
            raise ValueError("интервал не накрывает значение вероятности")
        return self


class Indicator(BaseModel):
    code: str
    label: str
    value: float
    unit: str
    as_of: date | None = None


class Driver(BaseModel):
    code: str
    label: str
    impact: str
    weight: float | None = None


class EvidenceBlock(BaseModel):
    """Результат бэктеста варианта."""

    status: BacktestStatus
    period_from: date | None = None
    period_to: date | None = None
    n_observations: int = 0
    n_regime: int = 0
    hit_rate: float | None = None
    baseline_hit_rate: float | None = None
    brier: float | None = None
    baseline_brier: float | None = None
    reason: str | None = None


class SignalVariant(BaseModel):
    """Один независимый сигнал."""

    variant: str
    variant_label: str
    status: SignalStatus
    verdict: Verdict | None = None
    headline: str | None = None
    probability: ProbabilityBlock | None = None
    indicators: list[Indicator] = Field(default_factory=list)
    drivers: list[Driver] = Field(default_factory=list)
    evidence: EvidenceBlock

    @model_validator(mode="after")
    def _no_verdict_without_evidence(self) -> SignalVariant:
        if self.evidence.status != BacktestStatus.passed:
            self.status = SignalStatus.insufficient_evidence
            self.verdict = None
            self.probability = None
            self.headline = None
        return self


class ComparisonBlock(BaseModel):
    leader: str | None
    metric: str
    verdict: str
    by_variant: dict[str, dict[str, float | int | None]]


class BenchmarkBlock(BaseModel):
    month: str
    as_of: date
    sme_rate: float
    key_rate: float
    premium_bp: float


class PolicyBlock(BaseModel):
    source: str
    p_borrow_now: float
    p_wait: float
    default: dict[str, float]
    recommended_verdict: Verdict | None = None


class SourceFreshness(BaseModel):
    name: str
    last_date: date | None
    stale: bool


class DataFreshness(BaseModel):
    stale: bool
    as_of: date
    sources: list[SourceFreshness]


class MoneySignals(BaseModel):
    """Ответ `/money/signals`: два независимых сигнала и сравнение."""

    as_of: date
    status: SignalStatus
    target: Target
    policy: PolicyBlock
    signals: list[SignalVariant]
    comparison: ComparisonBlock
    benchmark: BenchmarkBlock | None = None
    data: DataFreshness

    @model_validator(mode="after")
    def _stale_blocks_verdicts(self) -> MoneySignals:
        if self.data.stale or self.status == SignalStatus.stale_data:
            self.status = SignalStatus.stale_data
            for signal in self.signals:
                signal.status = SignalStatus.stale_data
                signal.verdict = None
                signal.probability = None
                signal.headline = None
        return self


class SpreadSeriesPoint(BaseModel):
    date: date
    premium_bp: float
    z_score: float | None = None


class SpreadSeries(BaseModel):
    variant: str
    label: str
    points: list[SpreadSeriesPoint]


class RatesPoint(BaseModel):
    month: str
    key_rate_avg: float
    sme_rate: float


class SeriesMeta(BaseModel):
    spread_last_date: date | None = None
    rates_last_month: str | None = None
    sources: list[str] = Field(default_factory=list)


class SeriesResponse(BaseModel):
    bucket: str
    spreads: list[SpreadSeries]
    rates: list[RatesPoint]
    meta: SeriesMeta


class PolicyItem(BaseModel):
    id: str
    label: str
    p_borrow_now: float
    p_wait: float
    is_default: bool


class PoliciesResponse(BaseModel):
    policies: list[PolicyItem]
    default: dict[str, float]


class PolicyQuery(BaseModel):
    """Query-параметры сигнала: только пороги политики."""

    model_config = ConfigDict(extra="forbid")

    p_borrow_now: float | None = Field(default=None, ge=0.0, le=1.0)
    p_wait: float | None = Field(default=None, ge=0.0, le=1.0)
    preset: str | None = None


class SeriesQuery(BaseModel):
    """Query-параметры серии."""

    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date
    bucket: str = "week"
