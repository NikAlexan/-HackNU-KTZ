# LocoTelemetry — Система мониторинга локомотивов

Симуляция бортовой телеметрии и диспетчерский дашборд для локомотивов **KZ8A** (электровоз) и **TE33A** (тепловоз).

---

## Архитектура

```
LocoAppBack (x4)          LocoDashboardBack          LocoDashboard
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  BCK-3 OnBoard  │─MQTT─▶│  MQTT Subscriber │─WS──▶│  Fleet UI   │
│  Simulator      │       │  Aggregator      │       │  Loco UI    │
│  WebSocket /ws  │◀──WS──│  REST API :9000  │◀─────│  Auth UI    │
└────────┬────────┘       └──────────────────┘       └─────────────┘
         │                        │
    PostgreSQL               PostgreSQL
  (locomotive_telemetry)   (loco_dashboard)
```

**LocoAppBack** — бортовой компьютер BCK-3. Один контейнер на локомотив. Симулирует телеметрию, считает износ
компонентов, отдаёт данные по WebSocket и публикует в MQTT.

**LocoDashboardBack** — серверная часть диспетчерского центра. Подписывается на MQTT, агрегирует данные каждые 60
секунд, хранит историю, отдаёт REST API для дашборда.

**LocoDashboard** — SPA на vanilla JS. Страница парка (`fleet.html`) и детальная страница локомотива (`loco.html`).

---

## Запуск

### 1. Общая сеть

```bash
docker network create loco_shared
```

### 2. LocoDashboardBack (MQTT-брокер + API)

```bash
cd LocoDashboardBack
docker compose up -d --build
```

Порты:

- `9000` — REST API и WebSocket дашборда
- `1883` — MQTT (EMQX)
- `18083` — EMQX Web Console
- `5433` — PostgreSQL дашборда

### 3. LocoAppBack (4 локомотива)

```bash
cd LocoAppBack
docker compose up -d --build
```

Порты бортовых WebSocket:
| Контейнер | Порт | ID | Тип |
|------------------|-------|-------------|---------|
| loco_kz8a_001 | 8000 | kz8a-001 | electro |
| loco_kz8a_002 | 8001 | kz8a-002 | electro |
| loco_te33a_001 | 8002 | te33a-001 | diesel |
| loco_te33a_002 | 8003 | te33a-002 | diesel |

### 4. LocoDashboard (UI)

```bash
cd LocoDashboard
docker compose up -d --build
```

Порт: `3000`

Открыть в браузере: [http://localhost:3000/login.html](http://localhost:3000/login.html)

Учётные данные по умолчанию: `admin` / `admin123`

---

## Компоненты системы

### LocoAppBack

```
main.py                         # FastAPI app, запускает generator и register
app/
  config.py                     # Env: LOCO_ID, LOCO_TYPE, LOCO_SERIES, ...
  generator.py                  # Фоновый цикл: simulate → sensors → health → WS/MQTT
  register.py                   # Регистрация локомотива в LocoDashboardBack при старте
  reporter.py                   # Периодическая отправка снапшота в LocoDashboardBack
  mqtt_publisher.py             # Публикация пакетов в MQTT (loco/{id}/telemetry)
  routers/
    ws.py                       # GET /ws — WebSocket стрим для бортового монитора
    maintenance.py              # POST /api/maintenance/repair|incident, GET /health
  telemetry/
    simulation.py               # Физическая модель (EMA скорость, сценарии)
    sensors_extract.py          # Плоский dict сенсоров из raw state
    health.py                   # ComponentHealthTracker, calc_health_from_config
    risk.py                     # compute_risk, compute_component_risk, sensor_cfgs
    packet.py                   # build_packet — сборка JSON для WS/MQTT
    sensors.py                  # build_sensors — legacy display с порогами
    node_config.py              # load_node_config — загрузка YAML
    node_config/
      kz8a_electro.yaml         # Конфиг компонентов KZ8A
      te33a_diesel.yaml         # Конфиг компонентов TE33A
```

### LocoDashboardBack

```
main.py                         # FastAPI app, запускает mqtt_subscriber
app/
  mqtt_subscriber.py            # Подписка MQTT, агрегация раз в 60с, обновление DB
  live_state.py                 # In-memory последний пакет + аккумулятор на агрегацию
  routers/
    auth.py                     # POST /auth/login (JWT), GET /auth/me
    locomotives.py              # GET /locomotives, GET /locomotives/{id}, POST /register
    ws.py                       # GET /ws/{loco_id} — WS прокси для дашборда
    ingest.py                   # POST /ingest — приём снапшотов от LocoAppBack
```

---

## Сенсоры и сценарии

### Типы сценариев (задаются автоматически или через API)

| Сценарий         | Описание                                           |
|------------------|----------------------------------------------------|
| `NORMAL_RUN`     | Нормальная эксплуатация                            |
| `OVERHEAT`       | Перегрев (масло / трансформатор) после t≥1800с     |
| `CRITICAL_ALERT` | Критический перегрев + аварийный код после t≥2700с |
| `VOLTAGE_SAG`    | Просадка напряжения КС (только KZ8A)               |

Переключить сценарий вручную:

```bash
curl -X POST http://localhost:8000/api/maintenance/incident \
  -H "X-API-Key: super-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "OVERHEAT"}'
```

### Маршрут симуляции

Локомотив непрерывно ездит по маршруту 0–120 км (2 плеча по 60 км, стоянки на конечных):

- **0–15% плеча** — разгон до 120 км/ч
- **15–80% плеча** — крейсерский ход
- **80–95% плеча** — торможение
- **95–100%** — стоянка

Скорость сглажена через EMA (α=0.25, постоянная ~2с).

---

## Система здоровья компонентов

### Принцип

Индекс здоровья — **монотонно убывающая** величина. Он считается как взвешенное среднее накопленного здоровья
компонентов (0–100 каждый). Каждый тик компонент теряет здоровье пропорционально мгновенному риску:

```
health[comp] -= risk * damage_rate * dt_sec
```

`component_risks` (мгновенные, колеблются) используются только для визуальных индикаторов риска.

### Компоненты KZ8A (электровоз)

| Компонент         | Вес | damage_rate | Сенсоры                              |
|-------------------|-----|-------------|--------------------------------------|
| transformer       | 1.5 | 0.05        | transformer_temp, pantograph_current |
| traction_drives   | 1.2 | 0.03        | td_currents_max                      |
| catenary_system   | 1.0 | 0.03        | catenary_v (band_outside 21–27.5 кВ) |
| pantograph        | 1.0 | 0.03        | pantograph_current                   |
| power_factor      | 0.8 | 0.015       | power_factor (cos φ)                 |
| power_electronics | 1.0 | 0.02        | power_kw (ratio к номиналу 8800 кВт) |
| brake_system      | 0.8 | 0.015       | brake (band_outside 4.5–5.8 атм)     |
| compressor        | 0.7 | 0.015       | compressor_temp, brake_fill_rate     |

### Компоненты TE33A (тепловоз)

| Компонент      | Вес | damage_rate | Сенсоры                               |
|----------------|-----|-------------|---------------------------------------|
| engine         | 2.0 | 0.08        | oil_temp, oil_pressure                |
| cooling_system | 1.3 | 0.04        | coolant_temp                          |
| turbocharger   | 1.2 | 0.04        | boost_pressure (band_outside 1.8–2.8) |
| engine_rpm     | 0.8 | 0.015       | engine_rpm (band_outside 450–1050)    |
| fuel_system    | 0.7 | 0.01        | fuel_level, fuel_consumption          |
| main_generator | 0.8 | 0.015       | main_gen_v (band_outside 480–580 В)   |
| brake_system   | 0.8 | 0.015       | brake (band_outside 4.5–5.8 атм)      |
| compressor     | 0.7 | 0.015       | compressor_temp, brake_fill_rate      |

### Ремонт компонентов

```bash
curl -X POST http://localhost:8000/api/maintenance/repair \
  -H "X-API-Key: super-secret-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"components": ["engine", "cooling_system"]}'
```

### Добавление нового типа локомотива

1. Создать `app/telemetry/node_config/{series}_{type}.yaml` по образцу существующих
2. Добавить ветку в `app/telemetry/sensors_extract.py` для извлечения сенсоров
3. Добавить ветки `init_state` / `evolve_state` в `simulation.py`
4. Запустить новый контейнер с `LOCO_TYPE`, `LOCO_SERIES`, `LOCO_NODE_CONFIG`

---

## API

### LocoAppBack (порты 8000–8003)

| Метод    | Путь                        | Описание                      |
|----------|-----------------------------|-------------------------------|
| `GET`    | `/ws`                       | WebSocket: стрим телеметрии   |
| `GET`    | `/api/maintenance/health`   | Текущее здоровье компонентов  |
| `POST`   | `/api/maintenance/repair`   | Сброс износа компонентов      |
| `POST`   | `/api/maintenance/incident` | Установить сценарий           |
| `DELETE` | `/api/maintenance/incident` | Снять принудительный сценарий |

### LocoDashboardBack (порт 9000)

| Метод  | Путь                    | Описание                       |
|--------|-------------------------|--------------------------------|
| `POST` | `/auth/login`           | Получить JWT токен             |
| `GET`  | `/auth/me`              | Текущий пользователь           |
| `GET`  | `/locomotives`          | Список всех локомотивов        |
| `GET`  | `/locomotives/{id}`     | Детали + история агрегатов     |
| `GET`  | `/ws/{loco_id}`         | WebSocket прокси к борту       |
| `POST` | `/locomotives/register` | Регистрация (вызывается BCK-3) |
| `POST` | `/ingest`               | Снапшот здоровья от BCK-3      |

---

## Переменные окружения

### LocoAppBack

| Переменная         | Описание                                  |
|--------------------|-------------------------------------------|
| `LOCO_ID`          | Уникальный ID (напр. `kz8a-001`)          |
| `LOCO_TYPE`        | `electro` или `diesel`                    |
| `LOCO_SERIES`      | Серия (напр. `KZ8A`, `TE33A`)             |
| `LOCO_NODE_CONFIG` | Путь к YAML конфигу компонентов           |
| `DATABASE_URL`     | AsyncPG URL бортовой БД                   |
| `DASHBOARD_URL`    | URL LocoDashboardBack для регистрации     |
| `REPORTER_API_KEY` | API-ключ для защиты maintenance endpoints |
| `MQTT_URL`         | URL MQTT-брокера                          |

### LocoDashboardBack

| Переменная       | Описание                              |
|------------------|---------------------------------------|
| `DATABASE_URL`   | AsyncPG URL БД дашборда               |
| `API_KEY`        | Ключ для приёма данных от LocoAppBack |
| `JWT_SECRET`     | Секрет для подписи JWT                |
| `ADMIN_USERNAME` | Логин администратора                  |
| `ADMIN_PASSWORD` | Пароль администратора                 |
| `MQTT_URL`       | URL MQTT-брокера                      |

---

## Структура WS-пакета (BCK-3)

```json
{
  "source": "BCK-3",
  "loco_id": "kz8a-001",
  "type": "electro",
  "series": "KZ8A",
  "ts": "2026-04-05T10:00:00Z",
  "step": 1234,
  "speed": 87.3,
  "traction_mode": "TRACTION",
  "km_position": 42,
  "error_code": null,
  "health_index": 98.4,
  "health_grade": "A",
  "component_health": {
    "transformer": 99.1,
    "traction_drives": 98.7,
    "...": "..."
  },
  "component_risks": {
    "transformer": 0.012,
    "...": "..."
  },
  "sensors": {
    "transformer_temp": 62.3,
    "catenary_v": 25.1,
    "...": "..."
  },
  "td_currents_a": [
    312,
    318,
    305,
    321,
    309,
    315,
    311,
    317
  ],
  "td_temps_c": [
    58.1,
    57.9,
    58.4,
    58.0,
    57.8,
    58.2,
    58.1,
    57.9
  ]
}
```