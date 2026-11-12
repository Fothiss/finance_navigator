"""Настройки приложения из переменных окружения.

Модельные параметры (`money_z_threshold`, `money_z_window`, `money_min_observations`)
задаются только здесь и не отдаются в API. Пороги политики (`money_p_borrow_now`,
`money_p_wait`) — значения по умолчанию: клиент может переопределить их в запросе.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class PolicyThresholds(BaseModel):
    """Пороги перевода вероятности в вердикт."""

    p_borrow_now: float = Field(ge=0.0, le=1.0)
    p_wait: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> PolicyThresholds:
        if self.p_wait >= self.p_borrow_now:
            raise ValueError("p_wait должен быть меньше p_borrow_now")
        return self


def default_presets() -> dict[str, PolicyThresholds]:
    """Именованные политики для селекта в интерфейсе."""
    return {
        "careful": PolicyThresholds(p_borrow_now=0.80, p_wait=0.55),
        "balanced": PolicyThresholds(p_borrow_now=0.65, p_wait=0.45),
        "aggressive": PolicyThresholds(p_borrow_now=0.50, p_wait=0.30),
    }


class Settings(BaseSettings):
    """Конфигурация приложения. Переопределяется переменными окружения `FN_*`."""

    model_config = SettingsConfigDict(env_prefix="FN_", env_file=".env", extra="ignore")

    # --- модельные параметры: в API не отдаются ---
    money_z_threshold: float = 1.0
    money_z_window: int = Field(default=250, ge=20)
    money_min_observations: int = Field(default=30, ge=1)
    money_min_lift: float = 0.02
    money_comparison_margin: float = 0.01
    money_forward_days: int = Field(default=30, ge=1)

    # --- политика решения ---
    money_p_borrow_now: float = 0.65
    money_p_wait: float = 0.45
    money_default_preset: str = "balanced"
    money_presets: dict[str, PolicyThresholds] = Field(default_factory=default_presets)

    # --- данные и сеть ---
    money_cache_ttl_seconds: int = Field(default=86_400, ge=60)
    money_stale_days: int = Field(default=5, ge=1)
    money_stale_days_sme: int = Field(default=75, ge=1)
    money_history_years: int = Field(default=10, ge=1, le=30)
    cbr_soap_url: str = "http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
    cbr_zcyc_url: str = "https://www.cbr.ru/hd_base/zcyc_params/"
    cbr_bulletin_page_url: str = "https://www.cbr.ru/statistics/bank_sector/sors/"
    moex_rusfar_url: str = (
        "https://iss.moex.com/iss/history/engines/stock/markets/index/securities/RUSFAR1M.json"
    )
    http_timeout_seconds: float = Field(default=40.0, gt=0)
    http_retries: int = Field(default=2, ge=0)
    cache_dir: Path = BACKEND_ROOT / ".cache"

    @model_validator(mode="after")
    def _validate_policy(self) -> Settings:
        PolicyThresholds(p_borrow_now=self.money_p_borrow_now, p_wait=self.money_p_wait)
        if not self.money_presets:
            raise ValueError("money_presets не может быть пустым")
        if self.money_default_preset not in self.money_presets:
            raise ValueError(
                f"дефолтный пресет {self.money_default_preset!r} отсутствует в money_presets"
            )
        return self

    def default_thresholds(self) -> PolicyThresholds:
        """Пороги политики по умолчанию."""
        return PolicyThresholds(p_borrow_now=self.money_p_borrow_now, p_wait=self.money_p_wait)


settings = Settings()
