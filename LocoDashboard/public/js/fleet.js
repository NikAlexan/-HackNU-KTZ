'use strict';

checkAuth(); // redirect to /login.html if no token

const DASHBOARD_WS_BASE = (window.__LOCO_CONFIG__ && window.__LOCO_CONFIG__.dashboardWsBaseUrl)
  || 'ws://127.0.0.1:9000';
const DASHBOARD_WS = `${DASHBOARD_WS_BASE}/ws/locomotives`;

// Clock
function tick() {
  const t = new Date().toLocaleTimeString('ru-RU');
  ['clk', 'fclk'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = t; });
}
tick();
setInterval(tick, 1000);

// Tab switching
let activeTab = 'log';

// ── helpers ──────────────────────────────────────────────────────────────────

function gradeClass(grade) {
  if (!grade) return 'b-blue';
  if (grade === 'A' || grade === 'B') return 'b-ok';
  if (grade === 'C') return 'b-warn';
  return 'b-crit';
}

function cardAlertClass(grade) {
  if (!grade) return '';
  if (grade === 'D' || grade === 'E') return ' alert';
  if (grade === 'C') return ' warn';
  return '';
}

function gradeBadgeLabel(grade, status) {
  if (grade === 'D' || grade === 'E') return 'АЛЕРТ';
  if (grade === 'C') return 'ВНИМАНИЕ';
  if (status === 'STOPPED') return 'СТОЯНКА';
  return 'НОРМА';
}

function metricColor(grade) {
  if (!grade || grade === 'A' || grade === 'B') return 'vg';
  if (grade === 'C') return 'vy';
  return 'vr';
}

function barFill(grade) {
  if (!grade || grade === 'A' || grade === 'B') return 'fg';
  if (grade === 'C') return 'fy';
  return 'fr';
}

function typeInfo(type) {
  const isElectro = type === 'ELECTRIC';
  return {
    isElectro,
    cardClass: isElectro ? 'el' : 'di',
    tagClass: isElectro ? 'el-tag' : 'di-tag',
    tagLabel: isElectro ? 'ЭЛЕКТРО' : 'ДИЗЕЛЬ',
    nameColor: isElectro ? 'var(--pur)' : 'var(--amb)',
  };
}

function fmt(v, digits = 1) {
  if (v === null || v === undefined) return '—';
  return Number(v).toFixed(digits);
}

function bar(pct, colorCls) {
  return `<div class="hb"><div class="hf ${colorCls}" style="width:${Math.min(100, Math.max(0, pct))}%"></div></div>`;
}

function mm(val, label, colorCls, pct, barCls) {
  return `<div class="mm"><div class="mv ${colorCls}">${val}</div><div class="ml">${label}</div>${bar(pct, barCls)}</div>`;
}

// ── component health mini bar ─────────────────────────────────────────────────

const _COMP_SHORT = {
  transformer:       'Тр',
  traction_drives:   'ТЭД',
  catenary_system:   'КС',
  pantograph:        'Пант',
  power_factor:      'cosφ',
  power_electronics: 'IGBT',
  brake_system:      'Торм',
  compressor:        'Комп',
  engine:            'Дв',
  cooling_system:    'Охл',
  turbocharger:      'ТКР',
  engine_rpm:        'Об/м',
  fuel_system:       'Топл',
  main_generator:    'Ген',
};

const _COMP_FULL = {
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

function buildCompGrid(componentHealth) {
  if (!componentHealth || !Object.keys(componentHealth).length) return '';
  const items = Object.entries(componentHealth).map(([comp, h]) => {
    const pct = Math.max(0, Math.min(100, h));
    const cc = pct >= 75 ? 'ch-ok' : pct >= 40 ? 'ch-warn' : 'ch-crit';
    const short = _COMP_SHORT[comp] || comp.slice(0, 3);
    const full = _COMP_FULL[comp] || comp;
    return `<div class="comp-item" title="${full}: ${pct.toFixed(0)}%">
      <div class="comp-val" style="color:${pct>=75?'var(--grn)':pct>=40?'var(--amb)':'var(--red)'}">${pct.toFixed(0)}</div>
      <div class="comp-bar-wrap"><div class="comp-bar-fill ${cc}" style="width:${pct}%"></div></div>
      <div class="comp-label">${short}</div>
    </div>`;
  }).join('');
  return `<div class="comp-grid">${items}</div>`;
}

// ── card builder ─────────────────────────────────────────────────────────────

function buildCard(loco) {
  const agg = loco.last_aggregate;
  const t = typeInfo(loco.type);

  if (!agg) {
    return `
<div class="loco-card ${t.cardClass}" onclick="location.href='/loco.html?id=${encodeURIComponent(loco.id)}'">
  <div class="head">
    <span class="lid" style="color:${t.nameColor}">${loco.number || loco.id}</span>
    <span class="ltype ${t.tagClass}">${t.tagLabel}</span>
    <span class="route">${loco.status === 'IN_MOTION' ? '🟢 В движении' : '🔵 Стоянка'}</span>
    <span class="badge b-blue">ОЖИДАНИЕ</span>
  </div>
  <div style="font-size:9px;color:var(--t3);padding:6px 2px">Ожидание первого агрегата (~1 мин после старта)</div>
</div>`;
  }
  const grade = agg ? agg.final_health_grade : loco.health_grade;
  const mc = metricColor(grade);
  const bc = barFill(grade);

  // Speed
  const speedVal = agg ? Math.round(agg.avg_speed_kmh || 0) : 0;
  const speedDisp = agg ? String(speedVal) : '—';

  // Temperature (raw number for color logic) — from metrics_json
  const amj = agg?.metrics_json || {};
  const tempKey = t.isElectro ? 'max_transformer_temp' : 'max_oil_temp';
  const tempRaw = amj[tempKey] ?? null;
  const tempDisp = tempRaw !== null ? fmt(tempRaw, 0) + '°' : '—';
  const tempColor = tempRaw === null ? 'vg' : tempRaw > 90 ? 'vr' : tempRaw > 75 ? 'vy' : 'vg';
  const tempBarCls = tempRaw === null ? 'fg' : tempRaw > 90 ? 'fr' : tempRaw > 75 ? 'fy' : 'fg';
  const tempPct = tempRaw !== null ? Math.round(tempRaw / 120 * 100) : 0;

  // Health
  const healthVal = agg ? fmt(agg.avg_health_index, 0) : fmt(loco.health_index, 0);
  const healthPct = agg ? Math.round(agg.avg_health_index || 0) : Math.round(loco.health_index || 0);

  // Readings count (4th cell)
  const readings = agg ? agg.readings_count : null;
  const readingsDisp = readings !== null ? String(readings) : '—';

  // 3rd cell: voltage (electro) or error count (diesel)
  let cell3;
  if (t.isElectro) {
    const v = amj.min_catenary_v ?? null;
    if (v !== null) {
      const vPct = Math.round(((v - 18) / (27 - 18)) * 100);
      const vColor = v < 21 ? 'vy' : 'vp';
      const vBar = v < 21 ? 'fy' : 'fp';
      cell3 = mm(fmt(v, 1) + 'кВ', 'сеть КС', vColor, vPct, vBar);
    } else {
      cell3 = mm('—', 'сеть КС', 'vp', 0, 'fp');
    }
  } else {
    const errCount = agg ? agg.error_count : 0;
    const errPct = errCount > 0 ? 100 : 5;
    cell3 = mm(String(errCount), 'ошибок', errCount > 0 ? 'vr' : 'vg', errPct, errCount > 0 ? 'fr' : 'fg');
  }

  const badgeCls = gradeClass(grade);
  const badgeLbl = gradeBadgeLabel(grade, loco.status);

  return `
<div class="loco-card ${t.cardClass}${cardAlertClass(grade)}" onclick="location.href='/loco.html?id=${encodeURIComponent(loco.id)}'">
  <div class="head">
    <span class="lid" style="color:${t.nameColor}">${loco.number || loco.id}</span>
    <span class="ltype ${t.tagClass}">${t.tagLabel}</span>
    <span class="route">${loco.status === 'IN_MOTION' ? '🟢 В движении' : '🔵 Стоянка'}</span>
    <span class="badge ${badgeCls}">${badgeLbl}</span>
  </div>
  <div class="metrics">
    ${mm(speedDisp, 'км/ч', 'vb', Math.round(speedVal / 120 * 100), 'fb')}
    ${mm(tempDisp, 'темп.', tempColor, tempPct, tempBarCls)}
    ${cell3}
    ${mm(readingsDisp, 'замеров', 'vb', readings !== null ? Math.round(readings / 120 * 100) : 0, 'fb')}
    <div class="mm" style="grid-column:span 2">
      <div class="mv ${mc}" style="font-size:11px">${healthVal}/${grade || '—'}</div>
      <div class="ml">индекс здоровья</div>
      ${bar(healthPct, bc)}
    </div>
  </div>
  ${buildCompGrid(loco.component_health)}
</div>`;
}

// ── KPI row ───────────────────────────────────────────────────────────────────

function renderKpi(locos) {
  const electro = locos.filter(l => l.type === 'ELECTRIC');
  const diesel = locos.filter(l => l.type === 'DIESEL');
  const inMotion = locos.filter(l => l.status === 'IN_MOTION');

  const crits = locos.filter(l => {
    const g = l.last_aggregate ? l.last_aggregate.final_health_grade : l.health_grade;
    return g === 'D' || g === 'E';
  });
  const warns = locos.filter(l => {
    const g = l.last_aggregate ? l.last_aggregate.final_health_grade : l.health_grade;
    return g === 'C';
  });

  const avgHealth = locos.length
    ? Math.round(locos.reduce((s, l) => s + (l.health_index || 0), 0) / locos.length)
    : 0;

  setText('kpi-electro', electro.length);
  setText('kpi-electro-motion', electro.filter(l => l.status === 'IN_MOTION').length + ' в движении');
  setText('kpi-diesel', diesel.length);
  setText('kpi-diesel-motion', diesel.filter(l => l.status === 'IN_MOTION').length + ' в движении');
  setText('kpi-alerts', crits.length + warns.length);
  setText('kpi-alerts-sub', crits.length + ' крит · ' + warns.length + ' внимание');
  setText('kpi-health', avgHealth);
  setText('kpi-health-sub', 'из 100 баллов');
  setText('kpi-total', locos.length);
  setText('kpi-motion', inMotion.length + ' в движении · ' + (locos.length - inMotion.length) + ' на стоянке');
}

// ── Cards ─────────────────────────────────────────────────────────────────────

function renderCards(locos) {
  const fleet = document.getElementById('fleet');
  if (!locos.length) {
    fleet.innerHTML = '<div class="empty-state"><div class="icon">🚂</div><div class="msg">Нет зарегистрированных локомотивов</div></div>';
    return;
  }

  const electro = locos.filter(l => l.type === 'ELECTRIC');
  const diesel = locos.filter(l => l.type === 'DIESEL');

  let html = '';
  if (electro.length) {
    html += `<div class="sec-title"><span style="width:10px;height:10px;border-radius:2px;background:var(--pur-m);display:inline-block"></span>Электровозы — 25 кВ AC</div>`;
    html += electro.map(buildCard).join('');
  }
  if (diesel.length) {
    html += `<div class="sec-title" style="margin-top:4px"><span style="width:10px;height:10px;border-radius:2px;background:var(--amb-m);display:inline-block"></span>Тепловозы — Дизель</div>`;
    html += diesel.map(buildCard).join('');
  }

  fleet.innerHTML = html;
}

// ── Event log ─────────────────────────────────────────────────────────────────

const _prevState = new Map(); // loco.id → { grade, status }

function addLogEntry(locos) {
  const now = new Date().toLocaleTimeString('ru-RU');
  let entries = '';

  locos.forEach(l => {
    const grade = l.last_aggregate ? l.last_aggregate.final_health_grade : l.health_grade;
    const prev = _prevState.get(l.id);

    // First arrival — just initialize, don't log
    if (!prev) {
      _prevState.set(l.id, { grade, status: l.status });
      return;
    }

    if (grade !== prev.grade) {
      const isCrit = grade === 'D' || grade === 'E';
      const isWarn = grade === 'C';
      const cls = isCrit ? 'crit' : isWarn ? 'warn' : 'ok';
      const dot = isCrit ? 'dr' : isWarn ? 'dw' : 'dok';
      entries += `<div class="ei ${cls}"><div class="ed ${dot}"></div><div class="et"><strong>${l.id}</strong> — оценка: ${prev.grade || '—'} → ${grade}<div class="etm">${now}</div></div></div>`;
    }

    if (l.status !== prev.status) {
      const moving = l.status === 'IN_MOTION';
      entries += `<div class="ei ok"><div class="ed dok"></div><div class="et"><strong>${l.id}</strong> — ${moving ? '🟢 начал движение' : '🔵 остановился'}<div class="etm">${now}</div></div></div>`;
    }

    _prevState.set(l.id, { grade, status: l.status });
  });

  if (!entries) return;
  const log = document.getElementById('event-log');
  if (!log) return;
  log.insertAdjacentHTML('afterbegin', entries);
  const items = log.querySelectorAll('.ei');
  for (let i = 30; i < items.length; i++) items[i].remove();
}

// ── Stats chart ───────────────────────────────────────────────────────────────

let statsChart = null;

function renderStats(locos) {
  // Only initialize chart when stats tab is visible to avoid 0-size canvas
  if (activeTab !== 'stats') {
    _pendingStatsData = locos;
    return;
  }
  _drawStats(locos);
  _pendingStatsData = null;
}

let _pendingStatsData = null;

function _drawStats(locos) {
  const grades = { A: 0, B: 0, C: 0, D: 0, E: 0 };
  locos.forEach(l => {
    const g = l.health_grade || 'A';
    if (g in grades) grades[g]++;
  });

  const canvas = document.getElementById('healthChart');
  if (!canvas) return;

  const vals = Object.values(grades);
  if (statsChart) {
    statsChart.data.datasets[0].data = vals;
    statsChart.update();
  } else {
    statsChart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['A', 'B', 'C', 'D', 'E'],
        datasets: [{
          data: vals,
          backgroundColor: ['#4ade80', '#86efac', '#f59e0b', '#ef4444', '#7f1d1d'],
          borderWidth: 1,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { size: 9 }, boxWidth: 10 } } },
        animation: { duration: 300 },
      }
    });
  }

  const inMotion = locos.filter(l => l.status === 'IN_MOTION').length;
  const stopped = locos.filter(l => l.status === 'STOPPED').length;
  const ss = document.getElementById('status-summary');
  if (ss) {
    ss.innerHTML = `
      <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:.5px solid var(--brd)">
        <span style="color:var(--t2)">В движении</span><span style="color:var(--grn)">${inMotion}</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:4px 0">
        <span style="color:var(--t2)">На стоянке</span><span style="color:var(--blue)">${stopped}</span>
      </div>`;
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setWsStatus(ok, msg) {
  const el = document.getElementById('ws-status');
  if (!el) return;
  el.textContent = msg;
  el.className = 'ws-status ' + (ok ? 'ws-ok' : 'ws-err');
}

function showTab(el, name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  el.classList.add('on');
  ['log', 'stats'].forEach(id => {
    const p = document.getElementById('t-' + id);
    if (p) p.style.display = id === name ? 'block' : 'none';
  });
  activeTab = name;
  if (name === 'stats') {
    if (_pendingStatsData) _drawStats(_pendingStatsData);
    else if (statsChart) statsChart.resize();
  }
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

let ws = null;

function connect() {
  setWsStatus(false, 'Подключение...');
  ws = new WebSocket(DASHBOARD_WS + '?token=' + encodeURIComponent(getToken()));

  ws.onopen = () => {
    setWsStatus(true, '● WS подключён');
    setText('sub', 'Электровозы + Тепловозы · Реалтайм');
    setText('fstat', 'WS: подключён | обновление каждые 3 сек');
  };

  ws.onmessage = (e) => {
    let locos;
    try { locos = JSON.parse(e.data); } catch { return; }
    renderKpi(locos);
    renderCards(locos);
    addLogEntry(locos);
    renderStats(locos);
  };

  ws.onclose = (e) => {
    if (e.code === 4001) { logout(); return; }
    setWsStatus(false, '● Нет соединения');
    setText('fstat', 'WS: отключён | переподключение через 5 сек...');
    setTimeout(connect, 5000);
  };

  ws.onerror = () => {
    setWsStatus(false, '● Ошибка WS');
  };
}

connect();
