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

  // Temperature — raw value for color logic
  const tempRaw = agg ? agg.max_temp_c : null;
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
    const v = agg && agg.min_voltage_kv !== null && agg.min_voltage_kv !== undefined ? agg.min_voltage_kv : null;
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
    const third = isElectro
      ? (a.min_voltage_kv !== null && a.min_voltage_kv !== undefined ? fmt(a.min_voltage_kv, 1) + ' кВ' : '—')
      : '—';
    const errStyle = a.error_count > 0 ? 'color:var(--red)' : 'color:var(--t3)';
    return `<tr>
      <td>${fmtTime(a.period_end)}</td>
      <td>${fmt(a.avg_speed_kmh, 0)} км/ч</td>
      <td>${fmt(a.max_temp_c, 0)} °C</td>
      <td>${third}</td>
      <td class="${gc}">${fmt(a.avg_health_index, 0)}</td>
      <td class="${gc}">${a.final_health_grade || '—'}</td>
      <td style="${errStyle}">${a.error_count}</td>
    </tr>`;
  }).join('');
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
    renderHeader(data);
    renderKpi(data);
    renderChart(data.recent_aggregates);
    renderTable(data.recent_aggregates, data.type);
  } catch (e) {
    setText('fstat', 'Ошибка: ' + e.message);
  }
}

fetchLoco();
setInterval(fetchLoco, 5000);