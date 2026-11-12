"""Служебный роутер: проверка живости сервиса."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Проверка, что сервис поднят."""
    return {"status": "ok", "service": "finance-navigator-backend", "module": "money"}
