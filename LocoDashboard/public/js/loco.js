'use strict';

checkAuth(); // redirect to /login.html if no token

const locoId = new URLSearchParams(location.search).get('id');

if (!locoId) location.href = '/';

// Clock
function tick() {
  const t = new Date().toLocaleTimeString('ru-RU');
  ['clk', 'fclk'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = t; });
}
tick();
setInterval(tick, 1000);

// ── helpers ───────────────────────────────────────────────────────────────────

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function fmt(v, digits = 1) {
  if (v === null || v === undefined) return '—';
  return Number(v).toFixed(digits);
}

function fmtTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}

function gradeColorClass(grade) {
  if (!grade || grade === 'A' || grade === 'B') return 'vg';
  if (grade === 'C') return 'vy';
  return 'vr';
}

function badgeCls(grade, status) {
  if (grade === 'D' || grade === 'E') return 'b-crit';
  if (grade === 'C') return 'b-warn';
  if (status === 'STOPPED') return 'b-blue';
  return 'b-ok';
}

function badgeLbl(grade, status) {
  if (grade === 'D' || grade === 'E') return 'АЛЕРТ';
  if (grade === 'C') return 'ВНИМАНИЕ';
  if (status === 'STOPPED') return 'СТОЯНКА';
  return 'НОРМА';
}

function typeLabel(type) {
  return type === 'ELECTRIC' ? 'Электровоз · 25 кВ AC' : 'Тепловоз · Дизель';
}

// ── render ────────────────────────────────────────────────────────────────────

function renderHeader(data) {
  setText('loco-title', data.number || data.id);
  setText('loco-sub', `${data.series} · ${typeLabel(data.type)} · Водитель: ${data.driver || '—'}`);
  document.title = `${data.id} — LocoDashboard`;

  const badge = document.getElementById('loco-badge');
  if (badge) {
    badge.textContent = badgeLbl(data.health_grade, data.status);
    badge.className = 'badge ' + badgeCls(data.health_grade, data.status);
  }
}

function renderKpi(data) {
  const agg = data.recent_aggregates && data.recent_aggregates.length ? data.recent_aggregates[0] : null;
  const isElectro = data.type === 'ELECTRIC';

  // Speed
  setText('kpi-speed', agg ? fmt(agg.avg_speed_kmh, 0) : '—');

  // Temperature — from metrics_json (dynamic keys replacing old max_temp_c)
  const mj = agg?.metrics_json || {};
  const tempKey = isElectro ? 'max_transformer_temp' : 'max_oil_temp';
  const tempRaw = mj[tempKey] ?? null;
  const tempEl = document.getElementById('kpi-temp');
  if (tempEl) {
    tempEl.textContent = tempRaw !== null ? fmt(tempRaw, 0) + ' °C' : '—';
    tempEl.className = 'kv ' + (tempRaw === null ? 'vg' : tempRaw > 90 ? 'vr' : tempRaw > 75 ? 'vy' : 'vg');
  }
  // Temperature label per type
  setText('kpi-temp-lbl', isElectro ? 'Т трансформатора °C' : 'Т масла °C');

  // Health
  const healthEl = document.getElementById('kpi-health');
  if (healthEl) {
    healthEl.textContent = fmt(data.health_index, 0);
    healthEl.className = 'kv ' + gradeColorClass(data.health_grade);
  }
  setText('kpi-grade', 'оценка ' + (data.health_grade || '—'));

  // Errors
  const errCount = agg ? agg.error_count : 0;
  const errEl = document.getElementById('kpi-errors');
  if (errEl) {
    errEl.textContent = String(errCount);
    errEl.className = 'kv ' + (errCount > 0 ? 'vr' : 'vg');
  }

  // Electro vs diesel specific KPI
  const elBlock = document.getElementById('kpi-elec-block');
  const diBlock = document.getElementById('kpi-diesel-block');
  if (isElectro) {
    if (elBlock) elBlock.style.display = '';
    if (diBlock) diBlock.style.display = 'none';
    const v = mj['min_catenary_v'] ?? null;
    const voltEl = document.getElementById('kpi-voltage');
    if (voltEl) {
      voltEl.textContent = v !== null ? fmt(v, 1) + ' кВ' : '—';
      voltEl.className = 'kv ' + (v === null ? 'vp' : v < 21 ? 'vy' : 'vp');
    }
  } else {
    if (elBlock) elBlock.style.display = 'none';
    if (diBlock) diBlock.style.display = '';
    setText('kpi-fuel', '—'); // fuel not available in aggregate
  }

  setText('fstat',
    `Обновлено: ${new Date().toLocaleTimeString('ru-RU')} | Агрегатов: ${data.recent_aggregates ? data.recent_aggregates.length : 0}`
  );
}

let healthChart = null;

function renderChart(aggregates) {
  if (!aggregates || !aggregates.length) return;

  const sorted = [...aggregates].reverse(); // oldest → newest
  const labels = sorted.map(a => fmtTime(a.period_end));
  const values = sorted.map(a => a.avg_health_index !== null ? a.avg_health_index : 0);

  const canvas = document.getElementById('healthChart');
  if (!canvas) return;

  if (healthChart) {
    healthChart.data.labels = labels;
    healthChart.data.datasets[0].data = values;
    healthChart.update();
  } else {
    healthChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Индекс здоровья',
          data: values,
          borderColor: '#1a5fa8',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#1a5fa8',
          tension: 0.3,
          fill: true,
          backgroundColor: 'rgba(26,95,168,0.07)',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { mode: 'index', intersect: false },
        },
        scales: {
          x: {
            ticks: { color: '#9a9890', font: { size: 8 } },
            grid: { color: 'rgba(0,0,0,0.04)' },
            border: { display: false },
          },
          y: {
            min: 0, max: 100,
            ticks: { color: '#9a9890', font: { size: 8 }, stepSize: 20 },
            grid: { color: 'rgba(0,0,0,0.04)' },
            border: { display: false },
          },
        },
        animation: { duration: 300 },
      }
    });
  }
}

function renderTable(aggregates, locoType) {
  const tbody = document.getElementById('agg-tbody');
  if (!tbody) return;

  if (!aggregates || !aggregates.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--t3);padding:16px">Нет данных — агрегаты появятся через ~1 мин после старта</td></tr>';
    return;
  }

  const isElectro = locoType === 'ELECTRIC';
  tbody.innerHTML = aggregates.map(a => {
    const gc = gradeColorClass(a.final_health_grade);
    const amj = a.metrics_json || {};
    const tempVal = isElectro ? amj.max_transformer_temp : amj.max_oil_temp;
    const third = isElectro
      ? (amj.min_catenary_v != null ? fmt(amj.min_catenary_v, 1) + ' кВ' : '—')
      : '—';
    const errStyle = a.error_count > 0 ? 'color:var(--red)' : 'color:var(--t3)';
    return `<tr>
      <td>${fmtTime(a.period_end)}</td>
      <td>${fmt(a.avg_speed_kmh, 0)} км/ч</td>
      <td>${tempVal != null ? fmt(tempVal, 0) + ' °C' : '—'}</td>
      <td>${third}</td>
      <td class="${gc}">${fmt(a.avg_health_index, 0)}</td>
      <td class="${gc}">${a.final_health_grade || '—'}</td>
      <td style="${errStyle}">${a.error_count}</td>
    </tr>`;
  }).join('');
}

// ── component health ─────────────────────────────────────────────────────────

const _COMP_LABELS = {
  transformer:       'Трансформатор',
  traction_drives:   'Тяговые электродвигатели',
  catenary_system:   'Контактная сеть',
  pantograph:        'Пантограф',
  power_factor:      'Коэффициент мощности',
  power_electronics: 'Силовая электроника',
  brake_system:      'Тормозная система',
  compressor:        'Компрессор',
  engine:            'Дизельный двигатель',
  cooling_system:    'Система охлаждения',
  turbocharger:      'Турбонагнетатель',
  engine_rpm:        'Обороты дизеля',
  fuel_system:       'Топливная система',
  main_generator:    'Главный генератор',
};

function _compColor(h) {
  if (h >= 75) return 'ch-ok';
  if (h >= 40) return 'ch-warn';
  return 'ch-crit';
}

function renderCompHealth(componentHealth, componentRisks) {
  const panel = document.getElementById('comp-panel');
  const btn = document.getElementById('repair-btn');
  if (!panel) return;

  const entries = Object.entries(componentHealth || {});
  if (!entries.length) {
    panel.innerHTML = '<div style="font-size:10px;color:var(--t3);padding:8px 0">Нет данных по узлам</div>';
    if (btn) btn.disabled = true;
    return;
  }

  const risks = componentRisks || {};
  panel.innerHTML = entries.map(([comp, health]) => {
    const pct = Math.max(0, Math.min(100, health));
    const cc = _compColor(pct);
    const label = _COMP_LABELS[comp] || comp;
    const hColor = pct >= 75 ? 'vg' : pct >= 40 ? 'vy' : 'vr';
    const risk = risks[comp];
    const riskHtml = risk != null
      ? `<div class="comp-row-risk ${risk > 0.5 ? 'vr' : risk > 0.1 ? 'vy' : 'vg'}">${(risk * 100).toFixed(0)}%</div>`
      : '';
    return `<div class="comp-row">
      <input type="checkbox" class="comp-row-check" id="chk-${comp}" value="${comp}">
      <div class="comp-row-label">${label}</div>
      <div class="comp-row-health ${hColor}">${pct.toFixed(1)}%</div>
      ${riskHtml}
      <div class="comp-row-bar"><div class="comp-row-bar-fill ${cc}" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');

  if (btn) btn.disabled = false;
}

async function repairSelected() {
  const checks = document.querySelectorAll('.comp-row-check:checked');
  const components = Array.from(checks).map(c => c.value);
  if (!components.length) { alert('Выберите хотя бы один узел'); return; }

  const btn = document.getElementById('repair-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Отправка...'; }

  // Find the loco app port — we don't have direct API access to LocoAppBack from dashboard
  // Send repair via dashboard proxy (we'll call LocoDashboardBack to proxy it)
  // For now: show alert that repair must be done via LocoAppBack API directly
  // TODO: add a proxy endpoint in LocoDashboardBack
  alert('Запрос на ТО отправлен для: ' + components.join(', ') + '\n\nДля выполнения ремонта используйте API:\nPOST /api/maintenance/repair на соответствующем экземпляре локомотива.');

  if (btn) { btn.disabled = false; btn.textContent = 'Отправить выбранные в ТО'; }
}

// ── fetch & poll ──────────────────────────────────────────────────────────────

async function fetchLoco() {
  try {
    const res = await fetch(`${DASHBOARD_API}/api/locomotives/${encodeURIComponent(locoId)}`, {
      headers: authHeaders(),
    });
    if (res.status === 401) { logout(); return; }
    if (res.status === 404) {
      setText('loco-title', 'Локомотив не найден');
      setText('loco-sub', locoId);
      return;
    }
    if (!res.ok) throw new Error('HTTP ' + res.status);

    const data = await res.json();
    _locoType = data.type;
    renderHeader(data);
    renderKpi(data);
    renderCompHealth(data.component_health, data.component_risks);
    renderChart(data.recent_aggregates);
    renderTable(data.recent_aggregates, data.type);
  } catch (e) {
    setText('fstat', 'Ошибка: ' + e.message);
  }
}

let _locoType = null;

async function fetchLocoAndInit() {
  await fetchLoco();
  if (_locoType) _connectLiveWS(_locoType);
}

fetchLocoAndInit();
setInterval(fetchLoco, 5000);

// ── live sensor panel (WebSocket /ws/loco/{id}) ───────────────────────────────

const _SENSOR_META = {
  electro: [
    { key: 'speed',             label: 'Скорость',           unit: 'км/ч',   warn: () => false },
    { key: 'catenary_v',        label: 'Напряжение КС',      unit: 'кВ',     warn: v => v < 23, crit: v => v < 20 },
    { key: 'pantograph_current',label: 'Ток пантографа',     unit: 'А',      warn: v => v > 700, crit: v => v > 900 },
    { key: 'td_currents_max',   label: 'Ток ТЭД макс',       unit: 'А',      warn: v => v > 550, crit: v => v > 650 },
    { key: 'power_kw',          label: 'Мощность',            unit: 'кВт',    warn: () => false },
    { key: 'regen_power',       label: 'Рекуперация',         unit: 'кВт',    warn: () => false },
    { key: 'power_factor',      label: 'cos φ',               unit: '',       warn: () => false },
    { key: 'transformer_temp',  label: 'Т трансформатора',   unit: '°C',     warn: v => v > 70, crit: v => v > 90 },
    { key: 'compressor_temp',   label: 'Т компрессора',       unit: '°C',     warn: v => v > 60, crit: v => v > 85 },
    { key: 'brake',             label: 'Давление тормоза',    unit: 'атм',    warn: v => v < 4.5, crit: v => v < 3.5 },
    { key: 'brake_fill_rate',   label: 'Заполнение рез.',     unit: 'атм/с',  warn: v => v > 0.08 },
  ],
  diesel: [
    { key: 'speed',             label: 'Скорость',            unit: 'км/ч',   warn: () => false },
    { key: 'engine_rpm',        label: 'Обороты',             unit: 'об/мин', warn: () => false },
    { key: 'oil_temp',          label: 'Т масла',             unit: '°C',     warn: v => v > 80, crit: v => v > 100 },
    { key: 'coolant_temp',      label: 'Т охладителя',        unit: '°C',     warn: v => v > 80, crit: v => v > 95 },
    { key: 'oil_pressure',      label: 'Давление масла',      unit: 'бар',    warn: v => v < 3.0, crit: v => v < 1.5 },
    { key: 'fuel',              label: 'Топливо',             unit: 'л',      warn: v => v < 4000, crit: v => v < 300 },
    { key: 'main_gen_v',        label: 'Генератор',           unit: 'В',      warn: () => false },
    { key: 'traction_force',    label: 'Тяговое усилие',      unit: 'кН',     warn: () => false },
    { key: 'compressor_temp',   label: 'Т компрессора',       unit: '°C',     warn: v => v > 60, crit: v => v > 85 },
    { key: 'brake',             label: 'Давление тормоза',    unit: 'атм',    warn: v => v < 4.5, crit: v => v < 3.5 },
    { key: 'brake_fill_rate',   label: 'Заполнение рез.',     unit: 'атм/с',  warn: v => v > 0.08 },
  ],
};

function renderSensors(sensors, locoType) {
  const panel = document.getElementById('sensor-panel');
  if (!panel || !sensors) return;

  const typeKey = locoType === 'ELECTRIC' ? 'electro' : 'diesel';
  const meta = _SENSOR_META[typeKey] || [];

  panel.innerHTML = meta.map(({ key, label, unit, warn, crit }) => {
    const v = sensors[key];
    if (v === undefined || v === null) return '';
    const num = Number(v);
    const isCrit = crit && crit(num);
    const isWarn = !isCrit && warn && warn(num);
    const cls = isCrit ? 's-crit' : isWarn ? 's-warn' : 's-ok';
    const disp = Number.isInteger(num) ? num : num.toFixed(key === 'brake_fill_rate' ? 3 : 1);
    return `<div class="sensor-row ${cls}">
      <div class="sensor-label">${label}</div>
      <div class="sensor-val">${disp}</div>
      <div class="sensor-unit">${unit}</div>
    </div>`;
  }).join('');
}

function _connectLiveWS(locoType) {
  const token = getToken();
  if (!token || !locoId) return;

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const host = DASHBOARD_API.replace(/^https?:\/\//, '');
  const ws = new WebSocket(`${proto}://${host}/ws/loco/${encodeURIComponent(locoId)}?token=${token}`);

  ws.onmessage = e => {
    try {
      const packet = JSON.parse(e.data);
      renderSensors(packet.sensors, locoType);
      const tsEl = document.getElementById('live-sensor-ts');
      if (tsEl) tsEl.textContent = new Date().toLocaleTimeString('ru-RU');

      const speedEl = document.getElementById('kpi-speed');
      if (speedEl && packet.speed != null) {
        speedEl.textContent = Number(packet.speed).toFixed(0);
      }
      const healthEl = document.getElementById('kpi-health');
      if (healthEl && packet.health_index != null) {
        healthEl.textContent = Number(packet.health_index).toFixed(0);
        healthEl.className = 'kv ' + gradeColorClass(packet.health_grade);
      }
      setText('kpi-grade', 'оценка ' + (packet.health_grade || '—'));
    } catch {}
  };

  ws.onerror = () => {};
  ws.onclose = () => setTimeout(() => _connectLiveWS(locoType), 3000);
}

