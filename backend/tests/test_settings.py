"""Тесты настроек: валидация политики на старте."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import Settings, default_presets


def test_settings_defaults_are_valid() -> None:
    cfg = Settings(_env_file=None)
    assert 0.0 <= cfg.money_p_borrow_now <= 1.0
    assert 0.0 <= cfg.money_p_wait < cfg.money_p_borrow_now
    assert cfg.money_default_preset in cfg.money_presets
    assert cfg.money_min_observations >= 1
    assert cfg.money_z_window >= 20


@pytest.mark.parametrize(
    ("p_borrow_now", "p_wait"),
    [
        (0.40, 0.50),  # порядок перепутан
        (0.50, 0.50),  # равны — недопустимо
        (-0.10, 0.20),  # отрицательный порог
        (1.20, 0.45),  # больше единицы
    ],
)
def test_settings_rejects_invalid_policy(p_borrow_now: float, p_wait: float) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            money_p_borrow_now=p_borrow_now,
            money_p_wait=p_wait,
        )


def test_settings_rejects_unknown_default_preset() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, money_default_preset="unknown")


def test_settings_rejects_broken_preset() -> None:
    presets = default_presets()
    presets["broken"] = presets["balanced"].model_copy(update={"p_wait": 0.99})
    with pytest.raises(ValidationError):
        Settings(_env_file=None, money_presets=presets)
