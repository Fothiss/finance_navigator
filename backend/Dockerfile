FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Зависимости дублируют backend/pyproject.toml: пакет не собирается как wheel
# (tool.uv.package = false), поэтому ставим их явно.
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn>=0.32" \
    "pydantic>=2.9" \
    "pydantic-settings>=2.6" \
    "httpx>=0.27" \
    "pandas>=2.2" \
    "cachetools>=5.5" \
    "openpyxl>=3.1.5"

COPY app ./app
COPY pyproject.toml ./

EXPOSE 8000

CMD ["python", "app/__main__.py"]
