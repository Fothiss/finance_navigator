"""Ошибки API в формате application/problem+json (RFC 7807)."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


class UpstreamUnavailableError(RuntimeError):
    """Внешний источник данных недоступен и кеша нет."""


class PolicyValidationError(ValueError):
    """Пороги политики или пресет не прошли валидацию."""


class NotFoundError(LookupError):
    """Запрошенный объект отсутствует."""


def problem(
    status_code: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Собрать ответ об ошибке в формате problem+json."""
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_MEDIA_TYPE)


async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 для ошибок валидации запроса и неизвестных параметров."""
    errors = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return problem(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Ошибка валидации запроса",
        "Параметры запроса некорректны.",
        "urn:finance-navigator:problem:validation",
        errors,
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Привести HTTPException к problem+json."""
    detail = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса."
    return problem(exc.status_code, "Ошибка запроса", detail)


async def upstream_handler(_: Request, exc: UpstreamUnavailableError) -> JSONResponse:
    """503 когда данные недоступны и кеша нет."""
    return problem(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Источник данных недоступен",
        str(exc) or "Внешний источник не ответил, кеш пуст.",
        "urn:finance-navigator:problem:upstream",
    )
