// ===== I18N =====
const i18n = {
  ru: {
    driver:'МАШИНИСТ: Карпов А.С.',telemetry:'ТЕЛЕМЕТРИЯ АКТИВНА',
    panel_traction:'Тяга и движение',traction_force:'Тяговое усилие',
    brake_pressure:'Давление тормозов',norm:'НОРМА',km_pos:'Позиция КМ',traction:'ТЯГА',
    axle_load:'Нагрузка на оси',axle1:'ось 1 (т)',axle2:'ось 2 (т)',axle3:'ось 3 (т)',axle4:'ось 4 (т)',
    speed:'Скорость',kmh:'КМ/Ч',health_grade:'A • НОРМА',health_idx:'Индекс здоровья',
    panel_resources:'Ресурсы и узлы',fuel:'Топливо',oil_temp:'Т масла двигателя',
    rpm:'Обороты дизеля',rpm_unit:'об/мин',alerts:'Активные алерты',
    alert1:'Т масла выше нормы (+8°C)',alert2:'Низкий уровень топлива — плановая заправка',
    alert3:'Тормозная система — норма',alert4:'Напряжение ГГ 530В — норма',
    loco_diagram:'Схема локомотива ТЭ33А',
    legend_title:'СОСТОЯНИЕ УЗЛОВ',legend_ok:'Норма',legend_warn:'Предупреждение',legend_crit:'Критично',
    legend_parts:'УЗЛЫ',leg_engine:'Дизель',leg_oil:'Масло двиг.',leg_fuel:'Топливо',leg_brakes:'Тормоза',
    chart_label:'Скорость • последние 60 сек',route:'Маршрут',from:'Откуда',to:'Куда',
    traveled:'Пройдено',arrival:'Прибытие',next_stop:'Следующий ост.',limits:'Ограничения',
    limit1_sub:'через 12 км (мост)',limit2_sub:'текущий участок',limit3_sub:'через 45 км',
    section:'СЕКЦИЯ А',delay:'Задержка: <span style="color:var(--accent2)">+0 мин</span>',ok:'ОК',ok2:'ОК',
  },
  kz: {
    driver:'МАШИНИСТ: Карпов А.С.',telemetry:'ТЕЛЕМЕТРИЯ БЕЛСЕНДІ',
    panel_traction:'Тарту және қозғалыс',traction_force:'Тарту күші',
    brake_pressure:'Тежеуіш қысымы',norm:'НОРМА',km_pos:'КМ позициясы',traction:'ТАРТУ',
    axle_load:'Осьтердегі жүктеме',axle1:'1-ось (т)',axle2:'2-ось (т)',axle3:'3-ось (т)',axle4:'4-ось (т)',
    speed:'Жылдамдық',kmh:'КМ/САҒ',health_grade:'A • НОРМА',health_idx:'Денсаулық индексі',
    panel_resources:'Ресурстар мен торабтар',fuel:'Отын',oil_temp:'Қозғалтқыш майының T°',
    rpm:'Дизель айналымы',rpm_unit:'айн/мин',alerts:'Белсенді ескертулер',
    alert1:'Май температурасы жоғары (+8°C)',alert2:'Отын деңгейі төмен — жоспарлы жанармай',
    alert3:'Тежеуіш жүйесі — норма',alert4:'ГГ кернеуі 530В — норма',
    loco_diagram:'ТЭ33А локомотив сызбасы',
    legend_title:'ТОРАП КҮЙІ',legend_ok:'Норма',legend_warn:'Ескерту',legend_crit:'Сыни',
    legend_parts:'ТОРАБТАР',leg_engine:'Дизель',leg_oil:'Қозғ. майы',leg_fuel:'Отын',leg_brakes:'Тежеуіш',
    chart_label:'Жылдамдық • соңғы 60 сек',route:'Маршрут',from:'Қайдан',to:'Қайда',
    traveled:'Өтілді',arrival:'Келу уақыты',next_stop:'Келесі аялдама',limits:'Шектеулер',
    limit1_sub:'12 км-ден кейін (көпір)',limit2_sub:'ағымдағы учаске',limit3_sub:'45 км-ден кейін',
    section:'А СЕКЦИЯ',delay:'Кешігу: <span style="color:var(--accent2)">+0 мин</span>',ok:'ОК',ok2:'ОК',
  }
};
function setLang(lang){
  const t=i18n[lang];
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const k=el.getAttribute('data-i18n');
    if(t[k]!==undefined) el.innerHTML=t[k];
  });
  document.getElementById('btn-ru').classList.toggle('active',lang==='ru');
  document.getElementById('btn-kz').classList.toggle('active',lang==='kz');
}

// ===== LOCOMOTIVE DIAGRAM STATUS =====
// Define which parts correspond to which alerts
// Status: 'ok' | 'warn' | 'crit'
const partStatus = {
  'part-engine':  'warn',   // oil temp high → engine warn
  'part-cooling': 'warn',   // oil/cooling related
  'part-fuel':    'warn',   // fuel < 50%
  'part-brakes':  'ok',     // brakes ok
  'part-cab':     'ok',
  'part-cab2':    'ok',
  'part-body':    'ok',
  'part-exhaust': 'ok',
  'part-generator':'ok',
};

function applyDiagramStatus() {
  for (const [id, status] of Object.entries(partStatus)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.classList.remove('loco-status-ok','loco-status-warn','loco-status-crit');
    el.classList.add('loco-status-' + status);
  }
  updateLegendDot('leg-engine', partStatus['part-engine']);
  updateLegendDot('leg-oil',    partStatus['part-engine']);
  updateLegendDot('leg-fuel',   partStatus['part-fuel']);
  updateLegendDot('leg-brakes', partStatus['part-brakes']);
}

function updateLegendDot(id, status) {
  const el = document.getElementById(id);
  if (!el) return;
  const colors = { ok:'rgba(0,255,136,0.3)', warn:'rgba(255,215,0,0.5)', crit:'rgba(255,68,68,0.5)' };
  const borders = { ok:'var(--accent2)', warn:'var(--accent4)', crit:'var(--warn)' };
  el.style.background = colors[status];
  el.style.borderColor = borders[status];
}

window.addEventListener('DOMContentLoaded', applyDiagramStatus);
if (document.readyState !== 'loading') applyDiagramStatus();

// ===== CHART =====
const speedData=[82,85,86,87,88,87,85,86,87,88,87,87,86,87,88,87,86,86,87,88,89,88,87,87,86,85,86,87,87,88,87,86,87,88,87,86,85,84,85,86,87,87,86,85,86,87,88,87,87,86,85,86,87,87,87,88,87,87,86,87];
const speedCanvas=document.getElementById('speedChart');
const speedCtx=speedCanvas.getContext('2d');
const speedChart=(window.Chart && speedCtx)?new Chart(speedCtx,{type:'line',data:{labels:speedData.map((_,i)=>i%10===0?-(60-i)+'s':''),datasets:[
  {data:speedData,borderColor:'#00d4ff',borderWidth:1.5,pointRadius:0,tension:0.35,fill:true,backgroundColor:'rgba(0,212,255,0.06)'},
  {data:speedData.map(()=>90),borderColor:'rgba(255,215,0,0.4)',borderWidth:1,borderDash:[4,4],pointRadius:0,fill:false}
]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
scales:{x:{display:false},y:{min:0,max:140,ticks:{color:'#4a6580',font:{size:9},stepSize:20},grid:{color:'rgba(255,255,255,0.04)'},border:{display:false}}},animation:{duration:0}}}):null;

// ===== CLOCK =====
function updateClock(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('ru-RU')}
updateClock(); setInterval(updateClock,1000);

// ===== SPEED: now from WebSocket =====

function applyDiagramStatusLive(partStatus){
  Object.entries(partStatus).forEach(([id,status])=>{
    const el=document.getElementById(id);
    if(!el) return;

    el.style.animation="";
    if(status==="ok"){
      el.style.filter="drop-shadow(0 0 6px #00ff88)";
      el.style.stroke="#00ff88";
    }
    if(status==="warn"){
      el.style.filter="drop-shadow(0 0 8px #ffd700)";
      el.style.stroke="#ffd700";
    }
    if(status==="crit"){
      el.style.filter="drop-shadow(0 0 10px #ff4444)";
      el.style.stroke="#ff4444";
      el.style.animation="blink-part 1s infinite";
    }
  });
}

function updateStatuses(data){
  const partStatus={};

  partStatus["part-brakes"]=data.pressure < 3 ? "crit" : data.pressure < 4.5 ? "warn" : "ok";
  partStatus["part-engine"]=data.oilTemp > 90 ? "crit" : data.oilTemp > 75 ? "warn" : "ok";
  partStatus["part-fuel"]=data.fuel < 20 ? "crit" : data.fuel < 50 ? "warn" : "ok";
  partStatus["part-cooling"]=data.coolingTemp > 95 ? "crit" : data.coolingTemp > 80 ? "warn" : "ok";

  applyDiagramStatusLive(partStatus);
}

const WS_URL = 'ws://localhost:8000/ws/loco/data';
let wsRetryTimer = null;
let smoothSpeedKmh = null;
let smoothPressure = null;
let smoothFuelPct = null;
let smoothOilTemp = null;
let smoothRpm = null;

function pickNumber(obj, keys) {
  for (const k of keys) {
    const v = obj?.[k];
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function pickString(obj, keys) {
  for (const k of keys) {
    const v = obj?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v);
  }
  return null;
}

function pickFuel(src) {
  const litersDirect = pickNumber(src, [
    'fuel_liters',
    'fuel_litres',
    'fuel_l',
    'fuel_volume_l',
    'fuel_volume',
    'fuel_level_l',
    'fuel_left_l',
    'fuel_remaining_l',
    'fuel_current_l',
  ]);

  const percentDirect = pickNumber(src, [
    'fuel_percent',
    'fuel_pct',
    'fuel_level_pct',
    'fuel_level_percent',
  ]);

  const fuelGeneric = pickNumber(src, ['fuel', 'fuel_level']);

  let fuelLiters = Number.isFinite(litersDirect) ? litersDirect : null;
  let fuelPercent = Number.isFinite(percentDirect) ? percentDirect : null;

  if (!Number.isFinite(fuelLiters) && Number.isFinite(fuelGeneric) && fuelGeneric > 100) {
    fuelLiters = fuelGeneric;
  }
  if (!Number.isFinite(fuelPercent) && Number.isFinite(fuelGeneric) && fuelGeneric >= 0 && fuelGeneric <= 100) {
    fuelPercent = fuelGeneric;
  }

  const tankCapacityL = pickNumber(src, [
    'fuel_tank_capacity_l',
    'fuel_capacity_l',
    'tank_capacity_l',
    'fuel_tank_l',
  ]);

  if (!Number.isFinite(fuelLiters) && Number.isFinite(fuelPercent)) {
    const cap = Number.isFinite(tankCapacityL) && tankCapacityL > 0 ? tankCapacityL : 6000;
    fuelLiters = (fuelPercent / 100) * cap;
  }
  if (!Number.isFinite(fuelPercent) && Number.isFinite(fuelLiters)) {
    const cap = Number.isFinite(tankCapacityL) && tankCapacityL > 0 ? tankCapacityL : 6000;
    fuelPercent = cap > 0 ? (fuelLiters / cap) * 100 : null;
  }

  return { fuelLiters, fuelPercent, tankCapacityL };
}

function smooth(prev, next, alpha = 0.25) {
  return prev === null ? next : (prev * (1 - alpha) + next * alpha);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setWidthPct(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = Math.max(0, Math.min(100, pct)).toFixed(0) + '%';
}

function setAlertState(rowId, status, text) {
  const row = document.getElementById(rowId);
  if (!row) return;
  row.classList.remove('ok', 'warn');
  if (status === 'ok') row.classList.add('ok');
  if (status === 'warn' || status === 'crit') row.classList.add('warn');
  if (text) {
    const span = row.querySelector('span');
    if (span) span.textContent = text;
  }
}

function readSensorValue(src, sensorKey) {
  const value = src?.sensors?.[sensorKey]?.value;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function readOilTempFromSensors(src) {
  const sensors = src?.sensors;
  if (!sensors || typeof sensors !== 'object') return null;
  for (const [key, sensor] of Object.entries(sensors)) {
    const label = String(sensor?.label ?? '').toLowerCase();
    const keyLc = key.toLowerCase();
    if (keyLc.includes('oil') || keyLc.includes('масл') || label.includes('oil') || label.includes('масл')) {
      const n = Number(sensor?.value);
      if (Number.isFinite(n)) return n;
    }
  }
  return null;
}

function drawSpeedChartFallback() {
  if (speedChart || !speedCtx || !speedCanvas) return;
  const w = speedCanvas.clientWidth || 420;
  const h = speedCanvas.clientHeight || 88;
  if (speedCanvas.width !== w || speedCanvas.height !== h) {
    speedCanvas.width = w;
    speedCanvas.height = h;
  }
  speedCtx.clearRect(0, 0, w, h);
  speedCtx.lineWidth = 1;
  speedCtx.strokeStyle = 'rgba(255,255,255,0.08)';
  for (let y = 0; y <= 140; y += 20) {
    const yy = h - (y / 140) * h;
    speedCtx.beginPath();
    speedCtx.moveTo(0, yy);
    speedCtx.lineTo(w, yy);
    speedCtx.stroke();
  }

  speedCtx.lineWidth = 1.5;
  speedCtx.strokeStyle = '#00d4ff';
  speedCtx.beginPath();
  for (let i = 0; i < speedData.length; i += 1) {
    const x = (i / Math.max(1, speedData.length - 1)) * w;
    const y = h - (Math.max(0, Math.min(140, speedData[i])) / 140) * h;
    if (i === 0) speedCtx.moveTo(x, y); else speedCtx.lineTo(x, y);
  }
  speedCtx.stroke();
}

function normalizePayload(raw) {
  const src = raw?.data && typeof raw.data === 'object' ? raw.data : raw;
  if (!src || typeof src !== 'object') return null;

  const type = String(src.type ?? '').toLowerCase().trim();
  if (type && type !== 'diesel') return null;

  const fuelInfo = pickFuel(src);
  const axleLoads = Array.isArray(src.axle_loads_t)
    ? src.axle_loads_t
    : (Array.isArray(src.axle_loads) ? src.axle_loads : null);

  return {
    type: type || null,
    speed: pickNumber(src, ['speed', 'velocity', 'v']),
    pressure: pickNumber(src, ['pressure', 'brake_pressure']) ?? readSensorValue(src, 'BRAKE_PRESSURE'),
    fuelPercent: Number.isFinite(fuelInfo.fuelPercent) ? fuelInfo.fuelPercent : null,
    fuelLiters: Number.isFinite(fuelInfo.fuelLiters) ? fuelInfo.fuelLiters : null,
    tankCapacityL: Number.isFinite(fuelInfo.tankCapacityL) ? fuelInfo.tankCapacityL : null,
    oilTemp: pickNumber(src, ['oilTemp', 'oil_temp', 'engine_oil_temp', 'engine_oil_temp_c', 'oil_temperature_c'])
      ?? readSensorValue(src, 'OIL_TEMP')
      ?? readSensorValue(src, 'ENGINE_OIL_TEMP')
      ?? readOilTempFromSensors(src)
      ?? readSensorValue(src, 'OVERHEAT'),
    coolingTemp: pickNumber(src, ['coolingTemp', 'cooling_temp', 'coolant_temp']),
    distanceKm: pickNumber(src, ['distanceKm', 'distance_km', 'distance']),
    tractionForceKn: pickNumber(src, ['traction_force_kn', 'tractive_effort_kn', 'traction_kn']),
    kmPosition: pickString(src, ['km_position', 'controller_position', 'controller_pos', 'step']),
    tractionMode: pickString(src, ['traction_mode', 'mode']),
    rpm: pickNumber(src, ['rpm', 'engine_rpm', 'diesel_rpm']),
    healthIndex: pickNumber(src, ['health_index', 'health']),
    healthGrade: pickString(src, ['health_grade']),
    ggVoltageV: pickNumber(src, ['generator_voltage_v', 'main_generator_voltage_v', 'voltage']),
    batteryV: pickNumber(src, ['battery_v', 'battery_voltage']),
    speedLimit: pickNumber(src, ['speed_limit_kmh', 'speed_limit']),
    axleLoads: axleLoads,
  };
}

function applyLiveData(d) {
  if (Number.isFinite(d.speed)) {
    const rawSpeed = Math.max(0, Math.min(140, d.speed));
    smoothSpeedKmh = smooth(smoothSpeedKmh, rawSpeed, 0.22);
    document.getElementById('spd').textContent = smoothSpeedKmh.toFixed(1);
    const arc = document.getElementById('speed-arc');
    const ratio = Math.max(0, Math.min(1, smoothSpeedKmh / 140));
    arc.setAttribute('stroke-dashoffset', String(355 - (355 * ratio)));
    if (speedChart) {
      speedData.push(smoothSpeedKmh);
      if (speedData.length > 60) speedData.shift();
      speedChart.data.datasets[0].data = speedData;
      speedChart.update('none');
    } else {
      speedData.push(smoothSpeedKmh);
      if (speedData.length > 60) speedData.shift();
      drawSpeedChartFallback();
    }
  }

  if (Number.isFinite(d.speedLimit)) {
    setText('speed-limit-val', d.speedLimit.toFixed(0));
  }

  if (Number.isFinite(d.tractionForceKn)) {
    const tractionKn = Math.max(0, d.tractionForceKn);
    setText('traction-val', tractionKn.toFixed(0));
    const tractionPct = Math.max(0, Math.min(100, (tractionKn / 300) * 100));
    setWidthPct('traction-bar', tractionPct);
    setText('traction-pct', tractionPct.toFixed(0) + '%');
  }

  if (Number.isFinite(d.pressure)) {
    smoothPressure = smooth(smoothPressure, d.pressure, 0.3);
    setText('brake-val', smoothPressure.toFixed(2));
    const pressPct = Math.max(0, Math.min(100, (smoothPressure / 7) * 100));
    setWidthPct('brake-bar', pressPct);
    const brakeStatus = document.getElementById('brake-status');
    if (brakeStatus) {
      if (smoothPressure < 3.5) {
        brakeStatus.textContent = 'КРИТИЧНО';
        brakeStatus.style.color = 'var(--warn)';
      } else if (smoothPressure < 4.5) {
        brakeStatus.textContent = 'ПРЕДУПР.';
        brakeStatus.style.color = 'var(--accent4)';
      } else {
        brakeStatus.textContent = 'НОРМА';
        brakeStatus.style.color = 'var(--accent2)';
      }
    }
  }

  if (d.kmPosition !== null) {
    const asNum = Number(d.kmPosition);
    setText('km-pos-val', Number.isFinite(asNum) ? `П-${asNum}` : d.kmPosition);
  }
  if (d.tractionMode) setText('traction-mode', d.tractionMode.toUpperCase());

  if (Array.isArray(d.axleLoads)) {
    for (let i = 0; i < 4; i += 1) {
      const n = Number(d.axleLoads[i]);
      if (Number.isFinite(n)) setText(`axle-${i + 1}-val`, n.toFixed(1));
    }
  }

  if (Number.isFinite(d.healthIndex)) {
    setText('health-score', d.healthIndex.toFixed(0));
  }
  if (d.healthGrade) {
    setText('health-grade', `${d.healthGrade.toUpperCase()} • НОРМА`);
  }

  if (Number.isFinite(d.fuelPercent) || Number.isFinite(d.fuelLiters)) {
    let fuelPct = d.fuelPercent;
    if (!Number.isFinite(fuelPct) && Number.isFinite(d.fuelLiters)) {
      const cap = Number.isFinite(d.tankCapacityL) && d.tankCapacityL > 0 ? d.tankCapacityL : 6000;
      fuelPct = Math.max(0, Math.min(100, (d.fuelLiters / cap) * 100));
    }
    if (Number.isFinite(fuelPct)) {
      smoothFuelPct = smooth(smoothFuelPct, fuelPct, 0.25);
      setWidthPct('fuel-bar', smoothFuelPct);
    }
    if (Number.isFinite(d.fuelLiters)) {
      setText('fuel-val', d.fuelLiters.toFixed(0));
      setText('fuel-unit', 'л');
      setText('fuel-pct', d.fuelLiters.toFixed(0) + ' л');
    } else if (Number.isFinite(d.fuelPercent)) {
      const cap = Number.isFinite(d.tankCapacityL) && d.tankCapacityL > 0 ? d.tankCapacityL : 6000;
      const litersFromPct = Math.max(0, (d.fuelPercent / 100) * cap);
      setText('fuel-val', litersFromPct.toFixed(0));
      setText('fuel-unit', 'л');
      setText('fuel-pct', litersFromPct.toFixed(0) + ' л');
    }
  }

  if (Number.isFinite(d.oilTemp)) {
    smoothOilTemp = smooth(smoothOilTemp, d.oilTemp, 0.25);
    setText('oil-temp-val', smoothOilTemp.toFixed(1));
    setWidthPct('oil-temp-bar', Math.max(0, Math.min(100, (smoothOilTemp / 120) * 100)));
    setText('oil-trend', smoothOilTemp > 85 ? '↑' : '→');
  }

  if (Number.isFinite(d.rpm)) {
    smoothRpm = smooth(smoothRpm, d.rpm, 0.2);
    setText('rpm-val', smoothRpm.toFixed(0));
    const rpmPct = Math.max(0, Math.min(100, (smoothRpm / 2400) * 100));
    setWidthPct('rpm-bar', rpmPct);
    setText('rpm-pct', rpmPct.toFixed(0) + '%');
  }

  if (Number.isFinite(d.distanceKm)) {
    document.getElementById('km-val').textContent = d.distanceKm.toFixed(1) + ' км';
  }

  if (Number.isFinite(d.ggVoltageV)) setText('gg-val', d.ggVoltageV.toFixed(0) + 'В');
  if (Number.isFinite(d.batteryV)) setText('akb-val', d.batteryV.toFixed(1) + 'В');

  const pressureForStatus = Number.isFinite(d.pressure) ? d.pressure : 5.2;
  const oilForStatus = Number.isFinite(d.oilTemp) ? d.oilTemp : 78;
  const capForFuel = (Number.isFinite(d.tankCapacityL) && d.tankCapacityL > 0) ? d.tankCapacityL : 6000;
  const fuelLitersForAlert = Number.isFinite(d.fuelLiters)
    ? d.fuelLiters
    : (Number.isFinite(d.fuelPercent) ? (d.fuelPercent / 100) * capForFuel : 2400);
  const fuelForStatus = Number.isFinite(d.fuelPercent)
    ? d.fuelPercent
    : (Number.isFinite(d.fuelLiters)
      ? (d.fuelLiters / capForFuel) * 100
      : 40);
  const coolingForStatus = Number.isFinite(d.coolingTemp) ? d.coolingTemp : 70;

  updateStatuses({
    pressure: pressureForStatus,
    oilTemp: oilForStatus,
    fuel: fuelForStatus,
    coolingTemp: coolingForStatus,
  });

  setAlertState(
    'alert1-row',
    oilForStatus > 75 ? 'warn' : 'ok',
    oilForStatus > 75 ? `Т масла выше нормы (${oilForStatus.toFixed(1)}°C)` : 'Т масла двигателя — норма'
  );
  setAlertState(
    'alert2-row',
    fuelForStatus < 50 ? 'warn' : 'ok',
    fuelForStatus < 50
      ? `Топливо ${fuelLitersForAlert.toFixed(0)} л — плановая заправка`
      : `Топливо ${fuelLitersForAlert.toFixed(0)} л — норма`
  );
  setAlertState(
    'alert3-row',
    pressureForStatus < 4.5 ? 'warn' : 'ok',
    pressureForStatus < 4.5 ? `Тормозная система — давление ${pressureForStatus.toFixed(2)} атм` : 'Тормозная система — норма'
  );
  const ggText = Number.isFinite(d.ggVoltageV) ? d.ggVoltageV.toFixed(0) : '530';
  setAlertState('alert4-row', 'ok', `Напряжение ГГ ${ggText}В — норма`);
}

function connectWS() {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const normalized = normalizePayload(parsed);
      if (normalized) applyLiveData(normalized);
    } catch (_err) {}
  };
  ws.onclose = () => {
    if (wsRetryTimer) clearTimeout(wsRetryTimer);
    wsRetryTimer = setTimeout(connectWS, 1500);
  };
  ws.onerror = () => {
    try { ws.close(); } catch (_e) {}
  };
}

connectWS();
drawSpeedChartFallback();
window.addEventListener('resize', drawSpeedChartFallback);
