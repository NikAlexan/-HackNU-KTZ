const path = require("path");
const http = require("http");
const express = require("express");
const { WebSocketServer } = require("ws");

const app = express();
const server = http.createServer(app);

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || "127.0.0.1";
const WS_PATH = "/local/data";

app.use(express.json({ limit: "64kb" }));
app.use("/assets", express.static(path.join(__dirname, "assets")));
app.use(
  express.static(path.join(__dirname), {
    index: false,
    extensions: false,
  })
);

let latestTelemetry = {
  type: "electro",
  fuel: 70.0,
  speed: 0.0,
  pressure: 5.5,
  voltage: 520.0,
  updatedAt: new Date().toISOString(),
};

const wss = new WebSocketServer({ noServer: true });

function asFloat(value, fallback = null) {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeType(value) {
  const raw = String(value ?? "").trim().toLowerCase();
  if (!raw) {
    return latestTelemetry.type;
  }
  if (raw === "1" || raw === "1.0" || raw.includes("electro") || raw.includes("electric")) {
    return "electro";
  }
  if (raw === "0" || raw === "0.0" || raw.includes("diesel")) {
    return "diesel";
  }
  return raw;
}

function normalizePayload(input = {}) {
  return {
    type: normalizeType(input.type ?? input.locomotiveType ?? input.engine_type),
    fuel: asFloat(input.fuel ?? input.fuel_level, latestTelemetry.fuel),
    speed: asFloat(input.speed ?? input.velocity, latestTelemetry.speed),
    pressure: asFloat(input.pressure ?? input.brake_pressure, latestTelemetry.pressure),
    voltage: asFloat(input.voltage ?? input.u, latestTelemetry.voltage),
    updatedAt: input.updatedAt || input.timestamp || new Date().toISOString(),
  };
}

function broadcastTelemetry(payload) {
  const message = JSON.stringify(payload);

  for (const client of wss.clients) {
    if (client.readyState === 1) {
      client.send(message);
    }
  }
}

function updateTelemetry(input, source = "api") {
  latestTelemetry = normalizePayload(input);
  broadcastTelemetry({ ...latestTelemetry, source });
  return latestTelemetry;
}

app.get("/", (_req, res) => {
  res.sendFile(path.join(__dirname, "panel-router.html"));
});

app.get("/panel", (_req, res) => {
  res.sendFile(path.join(__dirname, "panel-router.html"));
});

app.get("/driver", (_req, res) => {
  res.sendFile(path.join(__dirname, "driver-dashboard.html"));
});

app.get("/dispatcher", (_req, res) => {
  res.sendFile(path.join(__dirname, "dispatcher-dashboard.html"));
});

// Explicit routes requested by UI logic
app.get("/electro-driver-dashboard", (_req, res) => {
  res.sendFile(path.join(__dirname, "electro-driver-dashboard.html"));
});

app.get("/diesel-dispatcher-dashboard", (_req, res) => {
  res.sendFile(path.join(__dirname, "diesel-dispatcher-dashboard.html"));
});

// Backward-compat aliases (typo-safe)
app.get("/diesel-dispatche-dashboard", (_req, res) => {
  res.redirect("/diesel-dispatcher-dashboard");
});

app.get("/api/telemetry", (_req, res) => {
  res.json(latestTelemetry);
});

app.post("/api/telemetry", (req, res) => {
  try {
    const payload = updateTelemetry(req.body, "api");
    return res.status(200).json({ ok: true, telemetry: payload });
  } catch (error) {
    return res.status(400).json({ ok: false, error: "Invalid telemetry payload" });
  }
});

wss.on("connection", (socket) => {
  socket.send(JSON.stringify(latestTelemetry));

  socket.on("message", (raw) => {
    try {
      const incoming = JSON.parse(String(raw));
      updateTelemetry(incoming, "ws-client");
    } catch (_error) {
      // Ignore malformed client messages
    }
  });
});

server.on("upgrade", (request, socket, head) => {
  const url = new URL(request.url, `http://${request.headers.host}`);

  if (url.pathname !== WS_PATH) {
    socket.destroy();
    return;
  }

  wss.handleUpgrade(request, socket, head, (client) => {
    wss.emit("connection", client, request);
  });
});

let simulationTick = 0;
setInterval(() => {
  simulationTick += 1;

  // Keep app useful before real backend is connected.
  const synthetic = {
    type: simulationTick % 26 < 13 ? "electro" : "diesel",
    fuel: Math.max(5, latestTelemetry.fuel - 0.03),
    speed: 95 + Math.sin(simulationTick / 5) * 26,
    pressure: 5.4 + Math.sin(simulationTick / 7) * 0.6,
    voltage: 510 + Math.sin(simulationTick / 6) * 85,
    updatedAt: new Date().toISOString(),
  };

  updateTelemetry(synthetic, "sim");
}, 1000);

server.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
  console.log(`Unified panel:       http://localhost:${PORT}/panel`);
  console.log(`Electro dashboard:   http://localhost:${PORT}/electro-driver-dashboard`);
  console.log(`Diesel dashboard:    http://localhost:${PORT}/diesel-dispatcher-dashboard`);
  console.log(`WebSocket endpoint:  ws://localhost:${PORT}${WS_PATH}`);
  console.log(`Push API endpoint:   http://localhost:${PORT}/api/telemetry`);
});
