# Locomotive Dashboards (Node.js App)

## Run
```bash
npm install
npm start
```

Server starts on `http://localhost:3000` by default.

## Pages
- Driver dashboard: `http://localhost:3000/driver`
- Dispatcher dashboard: `http://localhost:3000/dispatcher`

## Telemetry channels
- WebSocket stream: `ws://localhost:3000/local/data`
- Pull latest snapshot: `GET /api/telemetry`
- Push new telemetry: `POST /api/telemetry`

## Expected telemetry payload
```json
{
  "type": "electro",
  "fuel": 63.4,
  "speed": 112.8,
  "pressure": 5.42,
  "voltage": 531.2,
  "updatedAt": "2026-04-04T07:21:00.000Z"
}
```

`type` can be string (`electro`/`diesel`) or float-like value:
- `1.0` -> `electro`
- `0.0` -> `diesel`

## Example: push telemetry from terminal
```bash
curl -X POST http://localhost:3000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"type":"diesel","fuel":48.7,"speed":84.2,"pressure":5.1,"voltage":510.4}'
```

## Notes
- Dashboards auto-connect to `/local/data`.
- Server includes synthetic telemetry so UI moves before real backend is connected.
