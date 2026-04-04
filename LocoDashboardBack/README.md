# LocoDashboardBack

FastAPI-сервис дашборда парка локомотивов. Принимает 1-минутные агрегаты от LocoAppBack, хранит историю телеметрии и предоставляет REST API + WebSocket для фронтенда.

## Архитектура

```
routers/
  ingest.py       — POST /api/telemetry/aggregate (приём агрегатов от LocoApp)
  locomotives.py  — REST API локомотивов + регистрация
  ws.py           — WebSocket /ws/locomotives (fleet-дашборд)
models.py         — Locomotive, TelemetryAggregate, Route, Event и др.
```

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg URL | `postgresql+asyncpg://dash_user:dash_pass@db:5432/loco_dashboard` |
| `API_KEY` | Bearer-токен для приёма агрегатов | `super-secret-key-change-me` |

`API_KEY` должен совпадать с `REPORTER_API_KEY` в LocoAppBack.

## Запуск

```bash
docker compose up -d
```

При старте автоматически применяются миграции (`alembic upgrade head`).

## API

### WebSocket

```
ws://localhost:9000/ws/locomotives
```

Стримит сводку по всем локомотивам каждые 3 секунды. Формат:

```json
[
  {
    "id": "kz8a-001",
    "series": "KZ8A",
    "number": "kz8a-001",
    "type": "DIESEL",
    "status": "IN_MOTION",
    "health_index": 98.5,
    "health_grade": "A",
    "last_aggregate": {
      "period_start": "2026-04-04T12:00:00+00:00",
      "period_end": "2026-04-04T12:01:00+00:00",
      "avg_speed_kmh": 87.3,
      "max_temp_c": 71.2,
      "min_voltage_kv": null,
      "avg_health_index": 98.5,
      "final_health_grade": "A",
      "readings_count": 119,
      "error_count": 0
    }
  }
]
```

`last_aggregate: null` если агрегатов ещё не поступало.

### REST

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/api/locomotives` | Список всех локомотивов со статусом и здоровьем |
| `GET` | `/api/locomotives/{loco_id}` | Детали локомотива + последние 12 агрегатов |
| `POST` | `/api/locomotives/register` | Регистрация локомотива (Bearer, вызывается LocoApp) |
| `POST` | `/api/telemetry/aggregate` | Приём 1-минутного агрегата (Bearer, вызывается LocoApp) |

### Пример: список локомотивов

```bash
curl http://localhost:9000/api/locomotives
```

```json
[
  {
    "id": "kz8a-001",
    "series": "KZ8A",
    "number": "kz8a-001",
    "type": "DIESEL",
    "driver": "Unknown",
    "status": "IN_MOTION",
    "health_index": 98.5,
    "health_grade": "A",
    "route_id": null
  }
]
```

## Безопасность

Эндпоинты `/api/telemetry/aggregate` и `/api/locomotives/register` защищены Bearer-токеном:

```bash
curl -X POST http://localhost:9000/api/telemetry/aggregate \
  -H "Authorization: Bearer super-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '...'
```

Без токена → `403 Not authenticated`
Неверный токен → `401 Invalid token`

## Статус локомотива

Обновляется автоматически при получении каждого агрегата:

| Условие | Статус |
|---|---|
| `avg_speed_kmh > 1` | `IN_MOTION` |
| `avg_speed_kmh ≤ 1` | `STOPPED` |

Также обновляются `health_index` и `health_grade`.

## База данных

```bash
# Применить миграции вручную
docker exec dashboard_back_api alembic upgrade head

# Подключиться к БД
docker exec -it dashboard_back_db psql -U dash_user -d loco_dashboard
```

Ключевые таблицы:

| Таблица | Описание |
|---|---|
| `locomotives` | Реестр локомотивов, текущий статус и здоровье |
| `telemetry_aggregates` | История 1-минутных агрегатов от LocoApp |
| `routes` | Маршруты |
| `events` | События и аварии |

## Сеть Docker

Контейнер `dashboard_back_api` создаёт сеть `loco_shared` (external для LocoApp). LocoApp подключается к этой сети для отправки агрегатов и регистрации.
