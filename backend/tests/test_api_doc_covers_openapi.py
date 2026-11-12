"""Контракты в docs/API.md должны совпадать с OpenAPI-схемой приложения."""

from __future__ import annotations

import re
from pathlib import Path

from app.main import app

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "API.md"
SECTION_RE = re.compile(r"^##\s+(GET|POST|PUT|PATCH|DELETE)\s+(\S+)\s*$", re.MULTILINE)


def openapi_operations() -> set[tuple[str, str]]:
    schema = app.openapi()
    return {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }


def documented_operations() -> set[tuple[str, str]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    return {(match.group(1), match.group(2)) for match in SECTION_RE.finditer(text)}


def test_api_doc_file_exists() -> None:
    assert DOC_PATH.exists(), f"нет файла документации {DOC_PATH}"


def test_api_doc_covers_openapi() -> None:
    missing = openapi_operations() - documented_operations()
    assert not missing, f"в docs/API.md нет разделов для операций: {sorted(missing)}"


def test_api_doc_has_no_extra_operations() -> None:
    extra = documented_operations() - openapi_operations()
    assert not extra, f"в docs/API.md описаны несуществующие операции: {sorted(extra)}"


def test_api_doc_mentions_error_codes() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for code in ("200", "422", "503"):
        assert code in text, f"в docs/API.md не описан код {code}"
