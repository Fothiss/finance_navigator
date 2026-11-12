"""Pydantic-записи внешних источников. Любые внешние данные проходят через них."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class KeyRatePoint(BaseModel):
    """Значение ключевой ставки на дату."""

    date: date
    rate: float = Field(gt=0, lt=100, description="Ставка, % годовых")


class OfzCurvePoint(BaseModel):
    """Точка кривой бескупонной доходности ОФЗ: тенор (лет) -> доходность, %."""

    date: date
    curve: dict[float, float]

    def tenor(self, years: float) -> float | None:
        """Доходность ближайшего тенорового значения (точное совпадение)."""
        return self.curve.get(float(years))


class RusfarPoint(BaseModel):
    """Значение индикатора RUSFAR на дату."""

    date: date
    rate: float = Field(gt=-50, lt=100, description="Ставка, % годовых")


class SmeRatePoint(BaseModel):
    """Средневзвешенная ставка по кредитам МСП за месяц."""

    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    rate_upto_1y: float = Field(gt=0, lt=100)
    rate_over_1y: float = Field(gt=0, lt=100)

    @property
    def rate(self) -> float:
        """Основная ставка бенчмарка — кредиты сроком свыше года."""
        return self.rate_over_1y
