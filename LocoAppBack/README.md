# LocoAppBack

FastAPI-сервис бортового компьютера локомотива (BCK-3). Генерирует телеметрию, стримит её по WebSocket и отправляет 1-минутные агрегаты в LocoDashboardBack.

## Архитектура

```
generator.py          — фоновая задача: генерация состояния + запись в БД
reporter.py           — фоновая задача: агрегация за 1 мин → POST в Dashboard
routers/ws.py         — WebSocket /ws/loco/data (стрим latest_packet)
register.py           — однократная регистрация локомотива в Dashboard при старте
telemetry/
  simulation.py       — физическая модель (скорость, температура, сценарии)
  sensors.py          — датчики OVERHEAT / VOLTAGE / BRAKE_PRESSURE
  packet.py           — сборка BCK-3 JSON пакета
```

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg URL | `postgresql+asyncpg://loco_user:loco_pass@db:5432/locomotive_telemetry` |
| `DASHBOARD_URL` | Адрес LocoDashboardBack | `http://dashboard_back_api:9000` |
| `LOCO_ID` | Идентификатор локомотива | `kz8a-001` |
| `LOCO_TYPE` | Тип тяги: `electro` или `diesel` | `diesel` |
| `LOCO_SERIES` | Серия локомотива | `KZ8A` |
| `REPORTER_API_KEY` | Bearer-токен для отправки агрегатов | `super-secret-key-change-me` |

## Запуск

```bash
docker compose up -d
```

При старте автоматически:
1. Применяются миграции (`alembic upgrade head`)
2. Локомотив регистрируется в LocoDashboardBack
3. Запускается генератор телеметрии
4. Запускается репортер (отправка агрегатов каждую минуту)

## API

### WebSocket

```
ws://localhost:8000/ws/loco/data
```

Стримит BCK-3 пакет каждые 500 мс. Формат:

```json
{
  "source": "BCK-3",
  "loco_id": "kz8a-001",
  "type": "diesel",
  "series": "KZ8A",
  "ts": "2026-04-04T12:00:00+00:00",
  "step": 42,
  "speed": 87.3,
  "traction_mode": "TRACTION",
  "km_position": 14,
  "battery_v": 109.2,
  "pressure": 5.1,
  "health_index": 98.5,
  "health_grade": "A",
  "error_code": null,
  "sensors": {
    "OVERHEAT": { "id": "SNS-TEMP", "value": 68.4, "unit": "°C", "status": "OK", ... },
    "BRAKE_PRESSURE": { "id": "SNS-BP", "value": 5.1, "unit": "атм", "status": "OK", ... }
  },
  "fuel": 11240.0,
  "engine_rpm": 820,
  "oil_temp_c": 71.2,
  ...
}
```

### HTTP

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/docs` | Swagger UI |

## Сценарии симуляции

Сценарий выбирается случайно при старте генератора:

| Сценарий | Описание |
|---|---|
| `NORMAL_RUN` | Штатный режим |
| `OVERHEAT` | Постепенный перегрев (после 30 мин) |
| `CRITICAL_ALERT` | Критическая авария (после 45 мин) |
| `VOLTAGE_SAG` | Просадка напряжения КС (только `electro`) |

## Профиль движения

Два перегона за цикл (1 час):
- **0–45%** цикла: разгон → крейсер 120 км/ч → торможение
- **45–50%**: стоянка на промежуточной станции
- **50–95%**: второй перегон
- **95–100%**: стоянка на конечной

## Расчёт индекса здоровья

Старт: 100 баллов. Штрафы:

| Условие | Штраф |
|---|---|
| Температура > 95°C | −25 |
| Напряжение < 20 кВ (electro) | −20 |
| Ток ТД > 650 А | −20 |
| Давление ТМ вне диапазона | −20 |
| Топливо < 20% (diesel) | −10 |
| Код ошибки | −2.5 / −5 |

Оценки: **A** ≥90, **B** ≥75, **C** ≥60, **D** ≥40, **E** <40

## База данных

Таблица `generated_readings` — индивидуальные показания каждые 500 мс. Используется репортером для агрегации.

```bash
# Применить миграции вручную
docker exec locomotive_back_api alembic upgrade head
```

## Сеть Docker

Контейнер `locomotive_back_api` подключён к сети `loco_shared` для связи с `dashboard_back_api`.
