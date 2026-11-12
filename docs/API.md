# API

Базовый URL локально: `http://127.0.0.1:8000`. Интерактивная схема — `/docs` (Swagger UI),
машинная — `/openapi.json`. Источник правды для типов — Pydantic-схемы в `backend/app/schemas/`;
этот документ описывает поведение и не должен с ними расходиться (проверяется тестом
`test_api_doc_covers_openapi`).

## Ошибки

Все ошибки отдаются в формате `application/problem+json` (RFC 7807):

```json
{
  "type": "urn:finance-navigator:problem:validation",
  "title": "Ошибка валидации запроса",
  "status": 422,
  "detail": "неизвестные параметры запроса: z_threshold"
}
```

| Код | Когда |
|---|---|
| 422 | параметры не прошли валидацию, неизвестный параметр, неверные пороги, неизвестный пресет |
| 503 | внешний источник недоступен и кеша нет |

Устаревшие данные — **не ошибка**: ответ 200 со `status: "stale_data"`.

---

## GET /api/v1/health

Проверка живости сервиса.

**Ответ 200**

```json
{"status": "ok", "service": "finance-navigator-backend", "module": "money"}
```

---

## GET /api/v1/money/signals

Два независимых сигнала о вероятности повышения ключевой ставки за 30 дней, их сравнение
и бенчмарк надбавки по ставкам МСП.

### Параметры

| Имя | Тип | Обязательный | Описание |
|---|---|---|---|
| `p_borrow_now` | float 0..1 | нет | порог вероятности для вердикта `borrow_now` |
| `p_wait` | float 0..1 | нет | порог вероятности для вердикта `wait` |
| `preset` | string | нет | идентификатор готовой политики (`careful`, `balanced`, `aggressive`) |

Пороги `p_borrow_now` и `p_wait` передаются только вместе. Порядок разрешения политики:
параметры запроса → пресет → значения по умолчанию из конфигурации (`0.65` / `0.45`).

Параметры модели (`z_threshold`, `z_window`, `min_observations`) в запросе запрещены: любой
неизвестный параметр даёт 422.

### Ответ 200

```json
{
  "as_of": "2026-11-12",
  "status": "ok",
  "target": {"event": "key_rate_up_forward_30d", "horizon_days": 30},
  "policy": {
    "source": "default",
    "p_borrow_now": 0.65,
    "p_wait": 0.45,
    "default": {"p_borrow_now": 0.65, "p_wait": 0.45},
    "recommended_verdict": null
  },
  "signals": [
    {
      "variant": "rusfar_term_premium",
      "variant_label": "Премия денежного рынка (RUSFAR 1M)",
      "status": "ok",
      "verdict": "wait",
      "headline": "Премия денежного рынка (RUSFAR 1M): премия к ключевой -30 б.п., z-score -0.9. Рынок не ждёт повышения ставки: решение о займе можно отложить.",
      "probability": {
        "event": "key_rate_up_forward_30d",
        "horizon_days": 30,
        "value": 0.1571,
        "interval_80": [0.0602, 0.3489],
        "model": {"name": "rule_zscore_threshold_1", "kind": "rule"},
        "baseline": {"name": "unconditional_base_rate", "value": 0.2619},
        "lift": -0.1048,
        "n_observations": 14,
        "threshold_z": 1.0
      },
      "indicators": [
        {"code": "key_rate", "label": "Ключевая ставка", "value": 14.0, "unit": "%", "as_of": "2026-11-12"},
        {"code": "rusfar_1m", "label": "RUSFAR 1M", "value": 14.01, "unit": "%", "as_of": "2026-11-11"}
      ],
      "drivers": [
        {"code": "premium_z", "label": "Премия за срок ниже обычного: рынок не ждёт ужесточения", "impact": "down", "weight": 0.9}
      ],
      "evidence": {
        "status": "passed",
        "period_from": "2019-04-30",
        "period_to": "2026-10-31",
        "n_observations": 84,
        "n_regime": 14,
        "hit_rate": 0.7381,
        "baseline_hit_rate": 0.7347,
        "brier": 0.1721,
        "baseline_brier": 0.1931
      }
    },
    {
      "variant": "ofz_curve_premium",
      "variant_label": "Премия кривой ОФЗ (1 год)",
      "status": "ok",
      "verdict": "wait",
      "headline": "...",
      "probability": {"value": 0.3571, "interval_80": [0.2291, 0.5038], "lift": -0.05, "n_observations": 28},
      "indicators": [],
      "drivers": [],
      "evidence": {"status": "passed", "n_observations": 90, "n_regime": 28}
    }
  ],
  "comparison": {
    "leader": "ofz_curve_premium",
    "metric": "brier",
    "verdict": "stable",
    "by_variant": {
      "rusfar_term_premium": {"hit_rate": 0.7381, "baseline_hit_rate": 0.7347, "brier": 0.1721, "baseline_brier": 0.1931, "n": 84},
      "ofz_curve_premium": {"hit_rate": 0.8293, "baseline_hit_rate": 0.7683, "brier": 0.1463, "baseline_brier": 0.1779, "n": 90}
    }
  },
  "benchmark": {
    "month": "2026-08",
    "as_of": "2026-08-31",
    "sme_rate": 14.22,
    "key_rate": 14.0,
    "premium_bp": 22.0
  },
  "data": {
    "stale": false,
    "as_of": "2026-11-12",
    "sources": [
      {"name": "cbr_key_rate", "last_date": "2026-11-12", "stale": false},
      {"name": "cbr_ofz_curve", "last_date": "2026-11-11", "stale": false},
      {"name": "moex_rusfar1m", "last_date": "2026-11-11", "stale": false},
      {"name": "cbr_sme_rates", "last_date": "2026-08-31", "stale": false}
    ]
  }
}
```

### Вердикты

| Вердикт | Условие | Смысл |
|---|---|---|
| `borrow_now` | `value >= p_borrow_now` | деньги дорожают: если кредит нужен в ближайшие 1–3 месяца, ставку лучше зафиксировать |
| `watch` | `p_wait <= value < p_borrow_now` | нет оснований действовать |
| `wait` | `value < p_wait` | повышения не ждём, заём можно отложить |

### Особые состояния

**`insufficient_evidence`** — бэктест не пройден (мало наблюдений, правило не выделяет режим,
прирост к baseline ниже порога) или данных для расчёта нет. `verdict` и `probability` равны `null`:

```json
{
  "status": "insufficient_evidence",
  "signals": [
    {
      "variant": "rusfar_term_premium",
      "status": "insufficient_evidence",
      "verdict": null,
      "probability": null,
      "evidence": {"status": "failed", "n_observations": 14, "reason": "мало наблюдений: 14 < 30"}
    }
  ]
}
```

**`stale_data`** — источник отстал больше чем на допуск (5 дней для дневных рядов, 75 дней для
месячной ставки МСП). Ответ 200, `verdict` и `probability` каждого варианта равны `null`:

```json
{"status": "stale_data", "data": {"stale": true, "sources": [{"name": "moex_rusfar1m", "last_date": "2026-01-05", "stale": true}]}}
```

### Коды

| Код | Описание |
|---|---|
| 200 | сигналы посчитаны (возможны `insufficient_evidence` и `stale_data` в теле) |
| 422 | неверные пороги, неизвестный пресет, неизвестный параметр |
| 503 | внешние источники недоступны и кеша нет |

### Примеры

```bash
curl "http://127.0.0.1:8000/api/v1/money/signals"
curl "http://127.0.0.1:8000/api/v1/money/signals?preset=careful"
curl "http://127.0.0.1:8000/api/v1/money/signals?p_borrow_now=0.70&p_wait=0.45"
curl "http://127.0.0.1:8000/api/v1/money/signals?p_borrow_now=0.4&p_wait=0.6"   # 422
curl "http://127.0.0.1:8000/api/v1/money/signals?z_threshold=5"                # 422
curl "http://127.0.0.1:8000/api/v1/money/signals?preset=nope"                  # 422
```

---

## GET /api/v1/money/series

Дневные премии за срок по обоим вариантам (с бакетированием) и помесячные ставки для бенчмарка.

### Параметры

| Имя | Тип | Обязательный | Описание |
|---|---|---|---|
| `from` | date `YYYY-MM-DD` | нет | начало диапазона, по умолчанию `to − 365 дней` |
| `to` | date `YYYY-MM-DD` | нет | конец диапазона, по умолчанию сегодня; не может быть в будущем |
| `bucket` | `day` \| `week` \| `month` | нет | бакет дневной серии, по умолчанию `week` |

Ограничения: `from <= to`, диапазон не длиннее 10 лет. `rates` не зависит от `bucket`.

### Ответ 200

```json
{
  "bucket": "week",
  "spreads": [
    {
      "variant": "rusfar_term_premium",
      "label": "Премия денежного рынка (RUSFAR 1M)",
      "points": [
        {"date": "2026-11-09", "premium_bp": -30.0, "z_score": -0.91}
      ]
    },
    {
      "variant": "ofz_curve_premium",
      "label": "Премия кривой ОФЗ (1 год)",
      "points": [
        {"date": "2026-11-09", "premium_bp": -25.0, "z_score": -0.64}
      ]
    }
  ],
  "rates": [
    {"month": "2026-08", "key_rate_avg": 14.0, "sme_rate": 14.22}
  ],
  "meta": {
    "spread_last_date": "2026-11-11",
    "rates_last_month": "2026-08",
    "sources": ["cbr_key_rate", "cbr_ofz_curve", "cbr_sme_rates", "moex_rusfar1m"]
  }
}
```

### Коды

| Код | Описание |
|---|---|
| 200 | серии посчитаны |
| 422 | `from` > `to`, `to` в будущем, диапазон длиннее 10 лет, неизвестный `bucket`, неизвестный параметр |
| 503 | внешние источники недоступны и кеша нет |

### Примеры

```bash
curl "http://127.0.0.1:8000/api/v1/money/series?from=2024-01-01&to=2026-11-12&bucket=week"
curl "http://127.0.0.1:8000/api/v1/money/series?from=2024-01-01&to=2026-11-12&bucket=month"
curl "http://127.0.0.1:8000/api/v1/money/series?from=2026-01-01&to=2024-01-01"  # 422
curl "http://127.0.0.1:8000/api/v1/money/series?from=2010-01-01&to=2026-01-01"  # 422 (> 10 лет)
curl "http://127.0.0.1:8000/api/v1/money/series?bucket=hour"                   # 422
```

---

## GET /api/v1/money/policies

Именованные политики для селекта в интерфейсе: интерфейс не дублирует числа в своём коде.

### Ответ 200

```json
{
  "policies": [
    {"id": "careful", "label": "Осторожная", "p_borrow_now": 0.8, "p_wait": 0.55, "is_default": false},
    {"id": "balanced", "label": "Сбалансированная", "p_borrow_now": 0.65, "p_wait": 0.45, "is_default": true},
    {"id": "aggressive", "label": "Агрессивная", "p_borrow_now": 0.5, "p_wait": 0.3, "is_default": false}
  ],
  "default": {"p_borrow_now": 0.65, "p_wait": 0.45}
}
```

Инварианты: ровно одна политика с `is_default: true`, для каждой `0 <= p_wait < p_borrow_now <= 1`.

### Коды

| Код | Описание |
|---|---|
| 200 | список политик |
| 503 | сервис не инициализирован (недоступен конфиг) |

### Пример

```bash
curl "http://127.0.0.1:8000/api/v1/money/policies"
```
