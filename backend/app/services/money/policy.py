"""Политика решения: пороги вероятности и перевод в вердикт."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.config.settings import PolicyThresholds, Settings


class Verdict(StrEnum):
    borrow_now = "borrow_now"
    watch = "watch"
    wait = "wait"


PRESET_LABELS: dict[str, str] = {
    "careful": "Осторожная",
    "balanced": "Сбалансированная",
    "aggressive": "Агрессивная",
}


@dataclass(frozen=True, slots=True)
class Policy:
    """Действующая политика: источник значений и сами пороги."""

    source: str
    p_borrow_now: float
    p_wait: float


def resolve_policy(
    cfg: Settings,
    p_borrow_now: float | None = None,
    p_wait: float | None = None,
    preset: str | None = None,
) -> Policy:
    """Порядок разрешения: query -> пресет -> дефолт конфига."""
    if p_borrow_now is not None or p_wait is not None:
        if p_borrow_now is None or p_wait is None:
            raise ValueError("пороги p_borrow_now и p_wait задаются только вместе")
        PolicyThresholds(p_borrow_now=p_borrow_now, p_wait=p_wait)
        return Policy(source="user", p_borrow_now=p_borrow_now, p_wait=p_wait)

    if preset is not None:
        if preset not in cfg.money_presets:
            raise KeyError(preset)
        thresholds = cfg.money_presets[preset]
        return Policy(
            source=f"preset:{preset}",
            p_borrow_now=thresholds.p_borrow_now,
            p_wait=thresholds.p_wait,
        )

    default = cfg.default_thresholds()
    return Policy(
        source="default",
        p_borrow_now=default.p_borrow_now,
        p_wait=default.p_wait,
    )


def decide(probability: float | None, policy: Policy) -> Verdict | None:
    """Перевести вероятность в вердикт по порогам политики."""
    if probability is None:
        return None
    if probability >= policy.p_borrow_now:
        return Verdict.borrow_now
    if probability < policy.p_wait:
        return Verdict.wait
    return Verdict.watch
