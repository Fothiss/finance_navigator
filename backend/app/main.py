"""Точка сборки FastAPI-приложения."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import settings
from app.errors import (
    UpstreamUnavailableError,
    http_exception_handler,
    upstream_handler,
    validation_handler,
)
from app.routers import health, money

app = FastAPI(
    title="Финансовый навигатор — API",
    version="0.1.0",
    description=(
        "Модуль 1 «Стоимость денег»: премия за срок и вероятность повышения ключевой ставки."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(UpstreamUnavailableError, upstream_handler)

app.include_router(health.router)
app.include_router(money.router)


def create_app() -> FastAPI:
    """Совместимость с фабрикой приложения для uvicorn."""
    return app


__all__ = ["app", "create_app", "settings"]
