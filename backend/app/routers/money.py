"""API модуля 1 «Стоимость денег». Только валидация и вызов сервиса."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.config.settings import settings
from app.deps import get_money_service
from app.schemas.money import MoneySignals, PoliciesResponse, SeriesResponse
from app.services.money.policy import Policy, resolve_policy
from app.services.money.series import BUCKETS
from app.services.money.service import MoneyService

router = APIRouter(prefix="/api/v1/money", tags=["money"])

SIGNAL_PARAMS = {"p_borrow_now", "p_wait", "preset"}
SERIES_PARAMS = {"from", "to", "bucket"}
MAX_RANGE_YEARS = 10


def _reject_unknown(request: Request, allowed: set[str]) -> None:
    unknown = sorted(set(request.query_params) - allowed)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"неизвестные параметры запроса: {', '.join(unknown)}",
        )


def _policy_from_query(request: Request) -> Policy:
    _reject_unknown(request, SIGNAL_PARAMS)
    params = request.query_params

    raw_borrow = params.get("p_borrow_now")
    raw_wait = params.get("p_wait")
    try:
        p_borrow_now = float(raw_borrow) if raw_borrow is not None else None
        p_wait = float(raw_wait) if raw_wait is not None else None
    except ValueError as exc:  # нечисловой порог
        raise HTTPException(
            status_code=422,
            detail="пороги p_borrow_now и p_wait должны быть числами",
        ) from exc

    preset = params.get("preset")
    try:
        return resolve_policy(settings, p_borrow_now=p_borrow_now, p_wait=p_wait, preset=preset)
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"неизвестный пресет: {exc.args[0]}",
        ) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"некорректные пороги политики: {exc}",
        ) from exc


def _parse_day(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"параметр {name} должен быть датой YYYY-MM-DD",
        ) from exc


@router.get("/signals", response_model=MoneySignals)
def get_signals(
    request: Request,
    service: Annotated[MoneyService, Depends(get_money_service)],
) -> MoneySignals:
    """Два независимых сигнала о вероятности повышения ключевой ставки."""
    policy = _policy_from_query(request)
    return service.get_signals(policy)


@router.get("/series", response_model=SeriesResponse)
def get_series(
    request: Request,
    service: Annotated[MoneyService, Depends(get_money_service)],
) -> SeriesResponse:
    """Премии за срок (оба варианта) и помесячные ставки для бенчмарка."""
    _reject_unknown(request, SERIES_PARAMS)
    params = request.query_params

    today = date.today()
    date_to = _parse_day(params["to"], "to") if "to" in params else today
    date_from = (
        _parse_day(params["from"], "from") if "from" in params else date_to - timedelta(days=365)
    )

    if date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="параметр from больше параметра to",
        )
    if date_to > today:
        raise HTTPException(
            status_code=422,
            detail="параметр to не может быть в будущем",
        )
    if (date_to - date_from).days > 365 * MAX_RANGE_YEARS:
        raise HTTPException(
            status_code=422,
            detail=f"диапазон не может быть длиннее {MAX_RANGE_YEARS} лет",
        )

    bucket = params.get("bucket", "week")
    if bucket not in BUCKETS:
        raise HTTPException(
            status_code=422,
            detail=f"параметр bucket должен быть одним из: {', '.join(BUCKETS)}",
        )

    return service.get_series(date_from, date_to, bucket)


@router.get("/policies", response_model=PoliciesResponse)
def get_policies(
    service: Annotated[MoneyService, Depends(get_money_service)],
) -> PoliciesResponse:
    """Именованные политики для селекта в интерфейсе."""
    return service.get_policies()
