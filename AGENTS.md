# AGENTS.md

## Role
You are a full-stack developer for this project. Reply briefly, focus on technical substance.

## Communication
- Always respond in Russian.
- Be concise. No filler words. No greetings, no closing remarks.
- Code examples over long explanations.

## Project Overview
Финансовый навигатор — веб-приложение для финдиректоров и владельцев среднего бизнеса.
Три модуля: «Стоимость денег» (спред RUONIA/ROISfix к ключевой ставке), «Валютный риск»
(волатильность корзины, аномалии, синхронность), «Налоговый прогноз» (прогноз выручки/расходов
на следующий месяц + расчёт налогов). ML не прогнозирует точечно — только вероятности событий
и интервалы. Все сигналы проверяются бэктестом на истории.

Стек: FastAPI + React SPA + PostgreSQL + Redis + ML (Prophet, gradient boosting). Всё в Docker Compose.

## Repository Layout

### Backend (`backend/`)
Layered architecture.
- `app/routers/` — API layer. One router per module (`money`, `risk`, `tax`, `profile`).
- `app/services/` — business logic. Расчёт спреда, волатильности, налогов, агрегация транзакций.
- `app/ml/` — модели, признаки, бэктест. Подпакеты `money/`, `risk/`, `tax/`.
- `app/data/` — загрузка и кеширование данных ЦБ, парсинг CSV.
- `app/clients/` — клиенты к внешним системам (ЦБ API, LLM при необходимости).
- `app/config/` — settings from env vars. Import `settings` singleton.
- `app/schemas/` — Pydantic request/response models.
- `app/models/` — SQLAlchemy models.

**Rule:** Routers parse request and call services. Logic lives in services. ML-модели не вызываются
из роутеров напрямую — только через сервисы.

### Frontend (`frontend/`)
SPA.
- `src/pages/` — экраны (Money, Risk, Tax, Profile, History).
- `src/components/` — переиспользуемые компоненты.
- `src/api/` — клиент к backend.
- `src/store/` — состояние приложения.

**Rule:** Компоненты — презентационные. Логика и запросы — в хуках/сторе/API-клиенте.

### Infra
- `docker-compose.yml` — оркестрация всех сервисов.
- `.env` — в корне проекта.

## Tech Stack

### Backend
- Python 3.12, `uv` package manager
- FastAPI + Uvicorn (port 8000)
- PostgreSQL — пользователи, профили, история сигналов, сохранённые транзакции
- Redis — кеш данных ЦБ (TTL 1 день), очередь фоновых задач
- ARQ (или Celery) — ежедневная выгрузка данных ЦБ
- ML: Prophet (прогноз выручки), scikit-learn / LightGBM (классификаторы вероятностей),
  pandas для агрегации
- Клиент ЦБ: официальный REST API (`https://www.cbr.ru/development/`), без ключа

### Frontend
- TypeScript, React + Vite
- Tailwind CSS, shadcn/ui
- Графики: Recharts или lightweight-charts
- API-клиент генерируется из OpenAPI FastAPI (`npm run gen:api`)

### Infra
- Docker Compose
- Nginx (опционально) — reverse proxy

## Commands

### Backend
- Run dev: `python app/__main__.py` (из `backend/`) — http://127.0.0.1:8000, `/docs` — Swagger
- Tests: `uv run pytest -v`
- Lint: `uv run ruff check .`
- Add dep: `uv add <package>`
- Синк данных ЦБ вручную: `python -m app.data.sync`

### Frontend
- Run dev: `npm run dev` — http://localhost:5173
- Build: `npm run build`
- Lint: `npm run lint`
- Tests: `npm run test`
- Типы из контракта: `npm run gen:api`

### Infra
- Up: `docker compose up -d`
- Logs: `docker compose logs -f <service>`
- Rebuild: `docker compose up -d --build <service>`

## Code Style — Zen of Python
Apply these when writing or reviewing code:
- Beautiful is better than ugly.
- Explicit is better than implicit.
- Simple is better than complex.
- Readability counts.
- Errors should never pass silently.

**Rules:**
- Type hints required (Python) / strict TypeScript.
- Use `uv add` for Python deps, `npm install` for JS deps.
- Log messages in English, comments/docstrings in Russian.
- Never log персональные данные пользователя или содержимое транзакций.
- ML-модели сохраняются в `backend/ml_artifacts/` (в `.gitignore`), версионируются по имени.
- Все внешние данные (ЦБ, CSV) проходят валидацию Pydantic-схемой перед попаданием в БД.
- Роутеры не содержат бизнес-логики — только валидация и вызов сервиса.

## Architecture Assessment (Before Any Change)
Before modifying code, evaluate architecture fit:

1. **Does this change fit current architecture?** If yes, proceed.
2. **If no, can architecture adapt slightly?** Small refactor OK. State what and why.
3. **If large architectural change needed,** stop and ask user first.

**Do not** silently reshape architecture for one feature. State assessment, propose minimal change, then implement.

## Domain Invariants
- **Не прогнозируем точечно.** Любой прогноз — вероятность события или интервал, не одно число.
  Нарушение этого инварианта — блокер.
- **Всегда есть baseline.** Любая ML-модель сравнивается с наивным прогнозом или простым правилом.
  Бэктест обязателен для каждого сигнала.
- **Данные ЦБ кешируются.** Роутеры не ходят в API ЦБ напрямую — только через сервис с Redis.
- **Модуль 3 прогнозирует базу, не налоги.** Налоги считаются арифметикой после прогноза выручки.
  Не смешивать эти слои.
- **CSV пользователя валидируется.** Если данных меньше 12 месяцев — прогноз с широким интервалом
  и предупреждением, не «тихий» результат.
- **Сигнал без бэктеста не выдаётся.** Если модель не прошла проверку на истории — эндпоинт
  возвращает `status: "insufficient_evidence"`, а не вердикт.
- Промпты (если появятся) и схемы structured output живут в `app/services/prompts/`, не inline.
- Смена ML-модели не должна требовать изменений в роутерах — только в `app/ml/`.
