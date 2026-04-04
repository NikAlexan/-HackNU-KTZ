(function () {
  const MAX_SPEED = 220;
  const DEFAULT_ENDPOINT = "/local/data";

  const role = document.body.dataset.role || "driver";
  const endpoint = normalizeEndpoint(new URLSearchParams(window.location.search).get("ws") || DEFAULT_ENDPOINT);

  const state = {
    type: null,
    fuel: null,
    speed: null,
    pressure: null,
    voltage: null,
    updatedAt: null,
  };

  let ws = null;
  let reconnectTimer = null;
  let firstRealData = false;
  let simulationTimer = null;

  const els = {
    endpoint: byId("endpoint"),
    clock: byId("clock"),
    status: byId("status"),
    statusText: byId("statusText"),
    updatedAt: byId("updatedAt"),

    speed: byId("speedVal"),
    speedGauge: byId("speedGauge"),

    type: byId("typeVal"),
    fuel: byId("fuelVal"),
    pressure: byId("pressureVal"),
    voltage: byId("voltageVal"),

    fuelBar: byId("fuelBar"),
    pressureBar: byId("pressureBar"),
    voltageBar: byId("voltageBar"),

    dType: byId("dType"),
    dFuel: byId("dFuel"),
    dSpeed: byId("dSpeed"),
    dPressure: byId("dPressure"),
    dVoltage: byId("dVoltage"),

    typeBadge: byId("typeBadge"),
    fuelBadge: byId("fuelBadge"),
    speedBadge: byId("speedBadge"),
    pressureBadge: byId("pressureBadge"),
    voltageBadge: byId("voltageBadge"),
  };

  setText(els.endpoint, endpoint);
  tickClock();
  setInterval(tickClock, 1000);

  render();
  connect();
  startSimulationIfNeeded();

  function connect() {
    setStatus("connecting", "Connecting...");

    try {
      ws = new WebSocket(endpoint);
    } catch (err) {
      setStatus("error", "WebSocket init failed");
      scheduleReconnect();
      return;
    }

    ws.onopen = function () {
      setStatus("connected", "Connected");
    };

    ws.onmessage = function (event) {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (err) {
        return;
      }

      const normalized = normalizePayload(payload);
      if (!normalized) {
        return;
      }

      firstRealData = true;
      stopSimulation();
      mergeState(normalized);
      render();
    };

    ws.onclose = function () {
      setStatus("error", "Disconnected");
      scheduleReconnect();
    };

    ws.onerror = function () {
      setStatus("error", "Socket error");
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      return;
    }
    reconnectTimer = window.setTimeout(function () {
      reconnectTimer = null;
      connect();
    }, 2000);
  }

  function normalizePayload(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    const source = Array.isArray(payload) ? payload[0] : payload;
    if (!source || typeof source !== "object") {
      return null;
    }

    return {
      type: source.type ?? source.locomotiveType ?? source.engine_type,
      fuel: parseMaybeFloat(source.fuel ?? source.fuel_level),
      speed: parseMaybeFloat(source.speed ?? source.velocity),
      pressure: parseMaybeFloat(source.pressure ?? source.brake_pressure),
      voltage: parseMaybeFloat(source.voltage ?? source.u),
      updatedAt: source.updatedAt || source.timestamp || new Date().toISOString(),
    };
  }

  function mergeState(next) {
    if (next.type !== undefined) state.type = next.type;
    if (next.fuel !== null && !Number.isNaN(next.fuel)) state.fuel = next.fuel;
    if (next.speed !== null && !Number.isNaN(next.speed)) state.speed = next.speed;
    if (next.pressure !== null && !Number.isNaN(next.pressure)) state.pressure = next.pressure;
    if (next.voltage !== null && !Number.isNaN(next.voltage)) state.voltage = next.voltage;
    if (next.updatedAt) state.updatedAt = next.updatedAt;
  }

  function render() {
    const speed = finiteOr(state.speed, 0);
    const fuel = finiteOr(state.fuel, 0);
    const pressure = finiteOr(state.pressure, 0);
    const voltage = finiteOr(state.voltage, 0);

    setText(els.speed, fmt(speed, 1));
    setText(els.type, formatType(state.type));
    setText(els.fuel, fmt(fuel, 1) + " %");
    setText(els.pressure, fmt(pressure, 2) + " bar");
    setText(els.voltage, fmt(voltage, 1) + " V");

    if (els.speedGauge) {
      const pct = clamp((speed / MAX_SPEED) * 100, 0, 100);
      els.speedGauge.style.setProperty("--pct", String(pct));
    }

    setBar(els.fuelBar, clamp(fuel, 0, 100));
    setBar(els.pressureBar, clamp((pressure / 10) * 100, 0, 100));
    setBar(els.voltageBar, clamp((voltage / 900) * 100, 0, 100));

    setText(els.updatedAt, formatTime(state.updatedAt));

    if (role === "dispatcher") {
      setText(els.dType, formatType(state.type));
      setText(els.dFuel, fmt(fuel, 1) + " %");
      setText(els.dSpeed, fmt(speed, 1) + " km/h");
      setText(els.dPressure, fmt(pressure, 2) + " bar");
      setText(els.dVoltage, fmt(voltage, 1) + " V");

      updateBadge(els.typeBadge, typeLevel(state.type));
      updateBadge(els.fuelBadge, fuel < 20 ? "crit" : fuel < 40 ? "warn" : "ok");
      updateBadge(els.speedBadge, speed > 170 ? "warn" : "ok");
      updateBadge(els.pressureBadge, pressure < 4 ? "crit" : pressure < 5 ? "warn" : "ok");
      updateBadge(els.voltageBadge, voltage < 350 ? "warn" : "ok");
    }
  }

  function startSimulationIfNeeded() {
    simulationTimer = window.setTimeout(function () {
      if (firstRealData) {
        return;
      }

      let tick = 0;
      setStatus("connecting", "No feed yet, simulation mode");

      simulationTimer = window.setInterval(function () {
        tick += 1;

        const synthetic = {
          type: tick % 30 < 14 ? "electro" : "diesel",
          fuel: 64 + Math.sin(tick / 10) * 18,
          speed: 86 + Math.sin(tick / 4) * 24,
          pressure: 5.5 + Math.sin(tick / 8) * 0.8,
          voltage: 520 + Math.sin(tick / 5) * 90,
          updatedAt: new Date().toISOString(),
        };

        mergeState(synthetic);
        render();
      }, 1000);
    }, 1200);
  }

  function stopSimulation() {
    if (simulationTimer) {
      clearTimeout(simulationTimer);
      clearInterval(simulationTimer);
      simulationTimer = null;
    }
  }

  function typeLevel(typeRaw) {
    const t = String(typeRaw || "").toLowerCase();
    if (t.includes("electro") || t.includes("electric") || t === "1" || t === "1.0") return "ok";
    if (t.includes("diesel") || t === "0" || t === "0.0") return "warn";
    return "warn";
  }

  function formatType(typeRaw) {
    const t = String(typeRaw || "").toLowerCase();

    if (!t) return "n/a";
    if (t.includes("electro") || t.includes("electric") || t === "1" || t === "1.0") return "electro";
    if (t.includes("diesel") || t === "0" || t === "0.0") return "diesel";

    return String(typeRaw);
  }

  function normalizeEndpoint(raw) {
    if (!raw) return DEFAULT_ENDPOINT;
    if (/^wss?:\/\//i.test(raw)) return raw;
    if (raw.startsWith("/")) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return proto + "//" + window.location.host + raw;
    }
    return "ws://" + raw;
  }

  function parseMaybeFloat(v) {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function fmt(value, digits) {
    return Number.isFinite(value) ? value.toFixed(digits) : "0";
  }

  function finiteOr(value, fallback) {
    return Number.isFinite(value) ? value : fallback;
  }

  function setText(el, text) {
    if (el) el.textContent = text;
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function setBar(el, pct) {
    if (!el) return;
    el.style.setProperty("--w", pct.toFixed(1) + "%");
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function setStatus(kind, text) {
    if (!els.status) return;

    els.status.classList.remove("connected", "error");

    if (kind === "connected") {
      els.status.classList.add("connected");
    } else if (kind === "error") {
      els.status.classList.add("error");
    }

    setText(els.statusText, text);
  }

  function updateBadge(el, kind) {
    if (!el) return;
    el.classList.remove("ok", "warn", "crit");
    el.classList.add(kind);
    el.textContent = kind;
  }

  function formatTime(raw) {
    if (!raw) return "n/a";
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return "n/a";
    return d.toLocaleTimeString();
  }

  function tickClock() {
    setText(els.clock, new Date().toLocaleTimeString());
  }
})();
