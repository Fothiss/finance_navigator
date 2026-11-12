# Tasks

## 1. Спайк данных

- [x] 1.1 Проверить `KeyRateXML` и `RuoniaXML` (SOAP): глубина, частота, поля; зафиксировать в `docs/DATA.md`
- [x] 1.2 Проверить ROISfix/MOSPRIME: подтвердить прекращение с 01.03.2022; зафиксировать в `docs/DATA.md`
- [x] 1.3 Сохранить сырые ответы `key_rate`, `ruonia`, `roisfix_empty` в `backend/tests/fixtures/cbr/`
- [x] 1.4 Проверить глубину истории кривой ОФЗ `hd_base/zcyc_params/` (постраничная выгрузка `UniDbQuery`); дописать строку в `docs/DATA.md`
- [x] 1.5 Проверить семантику и глубину RUSFAR1M (единицы `CLOSE`, с какого года, сопоставимость с RUONIA); дописать строку в `docs/DATA.md`
- [x] 1.6 Сохранить фикстуры КБД и RUSFAR1M в `backend/tests/fixtures/`

## 2. Каркас backend

- [x] 2.1 Создать дерево `backend/app/{routers,services,clients,data,config,schemas,models}`, `pyproject.toml` и зависимости через uv; проверка: `uv run python -c "import app"` из `backend/`
- [x] 2.2 Реализовать `config/settings.py`: пороги политики, пресеты, `z_threshold`, `z_window`, `min_observations`, TTL, URL ЦБ/MOEX, таймаут; валидация `0 <= p_wait < p_borrow_now <= 1` на старте; проверка: тест `test_settings_rejects_invalid_policy`
- [x] 2.3 Собрать `app/main.py` (роутеры, CORS `localhost:5173`, обработчики `problem+json` 422/503) и `app/__main__.py` (uvicorn 127.0.0.1:8000); проверка: `GET /api/v1/health` 200, `uv run ruff check .` чист
- [x] 2.4 Пакет `app/models/` с README (БД не нужна), `app/ml/` отсутствует

## 3. Клиенты и кеш

- [x] 3.1 `clients/cbr_client.py`: `KeyRateXML` (SOAP) + парсер КБД (HTML) + парсер бюллетеня МСП (xlsx, «Таблица 5»); таймаут, ретраи, Pydantic-валидация записей; проверка: тесты на фикстурах + тест битого ответа + таймаут на `httpx.MockTransport`
- [x] 3.2 `clients/moex_client.py`: `RUSFAR1M` из ISS JSON, пагинация истории; проверка: тест на фикстуре, тест на 200/404/429
- [x] 3.3 `data/cache.py`: `TTLCache` + JSON-снапшот `backend/.cache/`, «взять из кеша или загрузить»; проверка: два вызова → один HTTP, истечение TTL, ошибка не стирает кеш
- [x] 3.4 `data/sync.py`: ручное обновление снапшотов (`python -m app.data.sync`); проверка: пишет файлы и печатает даты источников

## 4. Сервисы расчёта

- [x] 4.1 `services/money/indicators.py`: премии `rusfar_term_premium_bp`, `ofz_curve_premium_bp` и их z-score по 250-дневному окну; проверка: unit-тесты на известных точках и отсутствие NaN-каскада
- [x] 4.2 `services/money/target.py`: событие `key_rate(t+30) > key_rate(t)` на месячной сетке; проверка: тест `test_money_no_lookahead` — обрезка датасета не меняет прошлые строки
- [x] 4.3 `services/money/rule.py`: условная частота по режиму z, интервал Уилсона 80%, baseline, lift, n; проверка: unit-тест на синтетическом датасете и краевые случаи (n=0, все/ни одного события)
- [x] 4.4 `services/money/backtest.py`: `hit_rate`, `baseline_hit_rate`, `brier`, `baseline_brier`, период, статус (`passed` при lift выше минимума и достаточном n), `comparison` (leader, metric=brier, verdict stable/inconclusive); проверка: тест «не лучше baseline → failed», «мало наблюдений → failed», «лидер по brier»
- [x] 4.5 `services/money/policy.py`: `resolve_policy` (query → пресет → дефолт), `decide`; проверка: параметризованный тест всех источников и границ порогов
- [x] 4.6 `services/money/benchmark.py`: надбавка `(sme_rate - key_rate)*100` и месячный ряд; проверка: тест на фикстуре бюллетеня
- [x] 4.7 `services/money/signal.py` и `services/money/series.py`: сборка ответов, бакетирование, свежесть источников; проверка: тест бакетов и «rates одинаков при разных бакетах»

## 5. Эндпоинт сигналов

- [x] 5.1 `app/schemas/money.py`: `ProbabilityBlock`, `BaselineInfo`, `ModelInfo`, `Indicator`, `Driver`, `BacktestEvidence`, `Policy`, `SignalVariant`, `Comparison`, `Benchmark`, `DataFreshness`, `MoneySignals` с `model_validator` (verdict/probability null при `evidence.status != passed`); проверка: тест схемы «failed → verdict None», «нет interval_80 → ValidationError»
- [x] 5.2 `routers/money.py::get_signals` с query-моделью `extra="forbid"`; проверка: 200 по полям, `?z_threshold=5` → 422 `problem+json`
- [x] 5.3 Покрыть тестами сценарии спеки: политика из запроса, дефолт, некорректные пороги (422), неизвестный пресет (422), `insufficient_evidence`, `stale_data`; проверка: `uv run pytest -v tests/test_money_signals.py`
- [x] 5.4 Описать `/api/v1/money/signals` в `docs/API.md` (параметры, порядок политики, примеры `ok`/`insufficient_evidence`/`stale_data`, коды 200/422/503)

## 6. Эндпоинты серии и политик

- [x] 6.1 `routers/money.py::get_series` с валидацией диапазона (`from <= to`, `to` не в будущем, не длиннее 10 лет) и `bucket` в `day|week|month`; проверка: 200 на валидном, 422 на каждом нарушении
- [x] 6.2 `routers/money.py::get_policies`: пресеты с признаком дефолтного; проверка: ровно один `is_default`, пороги монотонны, совпадает с `settings.money_presets`
- [x] 6.3 Покрыть тестами сценарии серии и пресетов; проверка: `uv run pytest -v tests/test_money_series.py tests/test_money_policies.py`
- [x] 6.4 Описать `/series` и `/policies` в `docs/API.md` с примерами; проверка: на каждый эндпоинт раздел с методом, путём, параметрами, примером, кодами 200/422/503

## 7. Каркас frontend

- [x] 7.1 Создать `frontend/` (Vite + React + TypeScript + Tailwind + Recharts), прокси `/api` на 127.0.0.1:8000; проверка: `npm run build` без ошибок
- [x] 7.2 `npm run gen:api` (openapi-typescript) и `src/api/client.ts`; проверка: типы `MoneySignals`, `SeriesResponse`, `PoliciesResponse` есть, strict TS собирается
- [x] 7.3 Роутинг и заглушки страниц `Money`, `Risk`, `Tax`, `Profile`, `History`; проверка: навигация работает, корневой маршрут ведёт на `Money`

## 8. Страница Money

- [x] 8.1 Хуки `useMoneySignals` и `useMoneySeries`: запрос с политикой, обработка 422/503 через `problem+json`, loading/error; проверка: unit-тест на мокнутом клиенте (успех, 422, 503)
- [x] 8.2 `PolicySelect`: пресеты из `/policies` + «свои пороги», состояние в URL, бейдж «политика изменена», показ `recommended_verdict`; проверка: тест «смена порога обновляет query», «невалидные пороги блокируют запрос»
- [x] 8.3 `SignalCard`: вердикт, `headline`, `probability.value` с маркерами порогов на шкале, состояния `insufficient_evidence`/`stale_data`; проверка: тест рендера трёх вердиктов и двух нештатных статусов
- [x] 8.4 `SpreadChart` (обе премии, б.п., полоса нормы, бакет) и `BenchmarkPanel` (надбавка МСП − ключевая); проверка: тест «данные из одного ответа `/series`», `npm run build` зелёный
- [x] 8.5 `ComparisonPanel`: лидер по brier, `stable`/`inconclusive`, hit_rate против baseline, пометка об in-sample оценке; проверка: тест рендера `stable` и `inconclusive`
- [x] 8.6 Собрать `pages/Money.tsx` из компонентов и `StaleBanner`; проверка: `npm run dev` против backend показывает реальные данные, `npm run lint` и `npm run build` зелёные

## 9. Запуск и интеграция

- [ ] 9.1 `.env.example` и `docker-compose.yml` (backend + frontend, без БД и Redis); проверка: `docker compose up -d`, `GET /api/v1/health` снаружи
- [x] 9.2 Обновить `README.md`: фактическая структура, команды модуля 1, ссылка на `docs/API.md`; проверка: команды выполняются как написано
- [x] 9.3 Тест `test_api_doc_covers_openapi` сверяет операции `/openapi.json` с разделами `docs/API.md`; проверка: зелёный при совпадении, красный при удалении раздела
- [x] 9.4 Полный прогон: `uv run pytest -v`, `uv run ruff check .`, `npm run lint`, `npm run build`, ручной сценарий «открыть /money → сменить пресет → увидеть смену вердиктов и `policy.source`»

## Workflow follow-up

- Заархивировать change `money-module-skeleton` после проверки артефактов и пройденных задач.
- Проверить появление `openspec/specs/money-spread/spec.md` после архивации.
