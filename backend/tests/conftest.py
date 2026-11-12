"""Общие фикстуры тестов backend."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"
ARTIFACTS = Path(__file__).parent / "_artifacts"


@pytest.fixture
def workdir() -> Iterator[Path]:
    """Рабочий каталог теста внутри репозитория (песочница чистит `tmp_path`)."""
    path = ARTIFACTS / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path


@pytest.fixture
def cfg(workdir: Path) -> Settings:
    """Настройки с временным каталогом кеша и без ретраев."""
    return Settings(
        _env_file=None,
        cache_dir=workdir / "cache",
        http_retries=0,
    )


@pytest.fixture
def api_factory(cfg: Settings):
    """Фабрика TestClient с подменённым датасетом вместо сети."""
    from fastapi.testclient import TestClient

    from app.deps import get_money_service
    from app.main import app
    from app.services.money.service import MoneyService

    def factory(dataset, today):
        service = MoneyService(
            cfg=cfg,
            cache=None,  # type: ignore[arg-type]
            cbr=None,  # type: ignore[arg-type]
            moex=None,  # type: ignore[arg-type]
            today=today,
        )
        service.dataset = lambda: dataset  # type: ignore[method-assign]
        app.dependency_overrides[get_money_service] = lambda: service
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def read_fixture(*parts: str) -> bytes:
    return FIXTURES.joinpath(*parts).read_bytes()


def read_text_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")
