// ===== I18N =====
const i18n = {
  ru: {
    tagline:'Машинист: Алтынбеков Р.М. &nbsp;|&nbsp; Нур-Султан → Кокшетау',
    speed:'Скорость',kmh:'КМ/Ч',speed_lim:'▲ ЛИМ 120',traction_motors:'Тяговые двигатели',
    td1_cur:'ТД1 ток',td2_cur:'ТД2 ток',td3_cur:'ТД3 ток',td4_cur:'ТД4 ток',
    td1_temp:'ТД1 °C',td4_temp:'ТД4 °C',km_pos:'Позиция КМ',traction:'ТЯГА',
    contact_net:'Контактная сеть',norm:'НОРМА',norm2:'НОРМА',norm3:'НОРМА',
    current:'Ток',power:'Мощность',regen_active:'Рекуперация активна',returned:'Возвращено',
    pantograph:'Пантограф',raised:'ПОДНЯТ',transformer_temp:'Т трансформ.',
    battery:'АКБ борт.',cooling:'Охлаждение',brake_pressure:'Давление тормозов',ept_ok:'ЭПТ ОК',
    health_idx:'Индекс здоровья',health_grade:'A • ОТЛИЧНО',alerts:'Алерты',
    alert1:'ТД4: ток +5% выше среднего',alert2:'ТД4: Т обмотки 82°C ↑',
    alert3:'Рекуперация 2.4 МВт — норма',alert4:'Трансформатор 71°C — норма',
    alert5:'ЭПТ / пневматика — норма',alert6:'СКИФ / КЛУБ-У — норма',
    route:'Маршрут',traveled:'Пройдено',arrival:'Прибытие',next_stop:'Следующий ост.',
    loco_diagram:'Схема локомотива КЗ8А',
    legend_title:'СОСТОЯНИЕ УЗЛОВ',legend_ok:'Норма',legend_warn:'Предупреждение',legend_crit:'Критично',
    legend_parts:'УЗЛЫ',leg_motors:'ТД / Инвертор',leg_transformer:'Трансформатор',
    leg_pantograph:'Пантограф',leg_cooling:'Охлаждение',leg_brakes:'Тормоза',
    chart_label:'Скорость + рекуперация • 60 сек',td_currents:'Токи ТД',speed_limits:'Ограничения скорости',
    limit1_sub:'через 8 км (кривая R=600)',limit2_sub:'текущий участок',limit3_sub:'через 35 км (перегон)',
    footer_left:'КЗ8А · №0021 &nbsp;|&nbsp; Секция А',
    footer_mid:'Задержка: <span>+0 мин</span> &nbsp;|&nbsp; СКИФ: ОК &nbsp;|&nbsp; КЛУБ-У: ОК &nbsp;|&nbsp; ТСКБМ: ОК',
  },
  kz: {
    tagline:'Машинист: Алтынбеков Р.М. &nbsp;|&nbsp; Нұр-Сұлтан → Көкшетау',
    speed:'Жылдамдық',kmh:'КМ/САҒ',speed_lim:'▲ ШЕК 120',traction_motors:'Тарту қозғалтқыштары',
    td1_cur:'ТҚ1 тогы',td2_cur:'ТҚ2 тогы',td3_cur:'ТҚ3 тогы',td4_cur:'ТҚ4 тогы',
    td1_temp:'ТҚ1 °C',td4_temp:'ТҚ4 °C',km_pos:'КМ позициясы',traction:'ТАРТУ',
    contact_net:'Жанасу желісі',norm:'НОРМА',norm2:'НОРМА',norm3:'НОРМА',
    current:'Тогы',power:'Қуаты',regen_active:'Рекуперация белсенді',returned:'Қайтарылды',
    pantograph:'Пантограф',raised:'КӨТЕРІЛГЕН',transformer_temp:'Трансформ. T°',
    battery:'Борттық АКБ',cooling:'Салқындату',brake_pressure:'Тежеуіш қысымы',ept_ok:'ЭТТ ОК',
    health_idx:'Денсаулық индексі',health_grade:'A • ӨТЕ ЖАҚСЫ',alerts:'Ескертулер',
    alert1:'ТҚ4: тогы орташадан +5% жоғары',alert2:'ТҚ4: орам температурасы 82°C ↑',
    alert3:'Рекуперация 2.4 МВт — норма',alert4:'Трансформатор 71°C — норма',
    alert5:'ЭТТ / пневматика — норма',alert6:'СКИФ / КЛУБ-У — норма',
    route:'Маршрут',traveled:'Өтілді',arrival:'Келу уақыты',next_stop:'Келесі аялдама',
    loco_diagram:'КЗ8А локомотив сызбасы',
    legend_title:'ТОРАП КҮЙІ',legend_ok:'Норма',legend_warn:'Ескерту',legend_crit:'Сыни',
    legend_parts:'ТОРАБТАР',leg_motors:'ТҚ / Инвертор',leg_transformer:'Трансформатор',
    leg_pantograph:'Пантограф',leg_cooling:'Салқындату',leg_brakes:'Тежеуіш',
    chart_label:'Жылдамдық + рекуперация • 60 сек',td_currents:'ТҚ тоғы',speed_limits:'Жылдамдық шектеулері',
    limit1_sub:'8 км-ден кейін (иін R=600)',limit2_sub:'ағымдағы учаске',limit3_sub:'35 км-ден кейін (аралық)',
    footer_left:'КЗ8А · №0021 &nbsp;|&nbsp; А Секция',
    footer_mid:'Кешігу: <span>+0 мин</span> &nbsp;|&nbsp; СКИФ: ОК &nbsp;|&nbsp; КЛУБ-У: ОК &nbsp;|&nbsp; ТСКБМ: ОК',
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
// TD4 has current and temp warnings → motors section warn
const partStatus = {
  'part-motors':      'warn',  // TD4 current/temp issue
  'part-transformer': 'ok',
  'part-pantograph':  'ok',
  'part-cooling':     'ok',
  'part-brakes':      'ok',
  'part-regen':       'ok',
  'part-cab':         'ok',
  'part-cab2':        'ok',
  'part-body':        'ok',
};

const partColors = {
  ok: {
    stroke: '#34d399',
    strokeWidth: '2.2',
    filter: 'drop-shadow(0 0 6px rgba(52,211,153,0.75)) drop-shadow(0 0 12px rgba(52,211,153,0.28))',
    anim: 'none',
    opacity: '1'
  },
  warn: {
    stroke: '#facc15',
    strokeWidth: '2.8',
    filter: 'drop-shadow(0 0 8px rgba(250,204,21,0.95)) drop-shadow(0 0 14px rgba(250,204,21,0.35))',
    anim: 'none',
    opacity: '1'
  },
  crit: {
    stroke: '#f87171',
    strokeWidth: '3.2',
    filter: 'drop-shadow(0 0 10px rgba(248,113,113,1)) drop-shadow(0 0 16px rgba(248,113,113,0.42))',
    anim: 'blink-crit 1.1s infinite',
    opacity: '1'
  },
};

const legendMap = {
  'leg-motors':      'part-motors',
  'leg-transformer': 'part-transformer',
  'leg-pantograph':  'part-pantograph',
  'leg-cooling':     'part-cooling',
  'leg-brakes':      'part-brakes',
};
const legendColors = {
  ok:   { bg:'rgba(52,211,153,0.3)',  border:'#34d399' },
  warn: { bg:'rgba(250,204,21,0.5)',  border:'#facc15' },
  crit: { bg:'rgba(248,113,113,0.5)', border:'#f87171' },
};

function applyDiagramStatus() {
  for (const [id, status] of Object.entries(partStatus)) {
    const el = document.getElementById(id);
    if (!el) continue;

    if (!el.dataset.baseStroke) {
      el.dataset.baseStroke = el.getAttribute('stroke') || '';
      el.dataset.baseStrokeWidth = el.getAttribute('stroke-width') || '';
      el.dataset.baseFilter = el.style.filter || '';
      el.dataset.baseAnimation = el.style.animation || '';
      el.dataset.baseOpacity = el.style.opacity || '1';
    }

    const c = partColors[status] || partColors.ok;
    const baseStroke = el.dataset.baseStroke;
    const baseStrokeWidth = el.dataset.baseStrokeWidth;

    el.style.stroke = c.stroke || baseStroke;
    el.style.strokeWidth = c.strokeWidth || baseStrokeWidth;
    el.style.filter = c.filter;
    el.style.animation = c.anim;
    el.style.opacity = c.opacity;
    el.style.vectorEffect = 'non-scaling-stroke';
    el.style.strokeLinecap = 'round';
    el.style.strokeLinejoin = 'round';
    el.style.paintOrder = 'stroke';
  }
  for (const [legId, partId] of Object.entries(legendMap)) {
    const el = document.getElementById(legId);
    if (!el) continue;
    const st = partStatus[partId] || 'ok';
    el.style.background = legendColors[st].bg;
    el.style.borderColor = legendColors[st].border;
  }
}
applyDiagramStatus();

// ===== CLOCK =====
function tick(){
  const t=new Date().toLocaleTimeString('ru-RU');
  document.getElementById('clk').textContent=t;
  document.getElementById('fclk').textContent=t;
}
tick(); setInterval(tick,1000);

// ===== LIVE DATA (WebSocket) =====
const WS_URL = 'ws://localhost:8000/ws/loco/data';
let wsRetryTimer = null;
let smoothVoltageKv = null;
let smoothSpeedKmh = null;
let speedRegenChart = null;
const chartSpeedData = Array.from({ length: 60 }, () => 0);
const chartRegenData = Array.from({ length: 60 }, () => 0);

function pickNumber(obj, keys) {
  for (const k of keys) {
    const v = obj?.[k];
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function normalizePayload(raw) {
  const src = raw?.data && typeof raw.data === 'object' ? raw.data : raw;
  if (!src || typeof src !== 'object') return null;

  return {
    type: String(src.type || '').toLowerCase(),
    speed: pickNumber(src, ['speed', 'velocity', 'v']),
    voltage: pickNumber(src, ['catenary_voltage_kv', 'voltage', 'u', 'line_voltage']),
    current: pickNumber(src, ['pantograph_current_a', 'current', 'i', 'amperage']),
    regenKw: pickNumber(src, ['regen_power_kw', 'regen', 'regeneration', 'regen_power']),
    powerKw: pickNumber(src, ['power_consumption_kw', 'power_kw']),
    batteryV: pickNumber(src, ['battery_v', 'battery_voltage']),
    fuel: pickNumber(src, ['fuel', 'fuel_level', 'fuel_percent']),
    pressure: pickNumber(src, ['pressure', 'brake_pressure']),
    healthIndex: pickNumber(src, ['health_index']),
    healthGrade: src.health_grade,
    oilTemp: pickNumber(src, ['oilTemp', 'oil_temp', 'engine_oil_temp', 'transformer_temp_c']),
    transformerTemp: pickNumber(src, ['transformer_temp_c']),
    coolingTemp: pickNumber(src, ['coolingTemp', 'cooling_temp', 'coolant_temp']),
    pantographUp: src.pantograph_up,
    sensors: src.sensors || {},
    tdCurrents: Array.isArray(src.td_currents_a) ? src.td_currents_a : [],
    tdTemps: Array.isArray(src.td_temps_c) ? src.td_temps_c : [],
  };
}

function applyLiveData(d) {
  if (d.type && d.type !== 'electro') return;

  const speed = Number.isFinite(d.speed) ? Math.max(0, Math.min(220, d.speed)) : null;
  const voltage = Number.isFinite(d.voltage) ? Math.max(0, Math.min(25, d.voltage)) : null;
  const current = d.current;
  const regen = d.regenKw;

  if (Number.isFinite(speed)) {
    smoothSpeedKmh = smoothSpeedKmh === null ? speed : (smoothSpeedKmh * 0.75 + speed * 0.25);
    document.getElementById('spd').textContent = smoothSpeedKmh.toFixed(1);
  }
  if (Number.isFinite(voltage)) {
    smoothVoltageKv = smoothVoltageKv === null ? voltage : (smoothVoltageKv * 0.7 + voltage * 0.3);
    document.getElementById('vlt').textContent = smoothVoltageKv.toFixed(2);
    // For electro panel ring, 25кВ is full scale.
    const arc = document.getElementById('varc');
    const ratio = Math.max(0, Math.min(1, smoothVoltageKv / 25));
    arc.setAttribute('stroke-dashoffset', String(323 - 323 * ratio));
  }
  if (Number.isFinite(current)) document.getElementById('cur').textContent = Math.round(current) + 'А';
  if (Number.isFinite(regen)) document.getElementById('regen').textContent = (regen / 1000).toFixed(2) + ' МВт';
  if (Number.isFinite(d.powerKw)) document.getElementById('powerVal').textContent = d.powerKw.toFixed(1) + 'кВт';

  if (speedRegenChart) {
    const speedForChart = Number.isFinite(speed) ? speed : (Number.isFinite(chartSpeedData[chartSpeedData.length - 1]) ? chartSpeedData[chartSpeedData.length - 1] : 0);
    const regenForChartMw = Number.isFinite(regen) ? Math.max(0, regen / 1000) : 0;
    chartSpeedData.push(speedForChart);
    chartRegenData.push(regenForChartMw);
    if (chartSpeedData.length > 60) chartSpeedData.shift();
    if (chartRegenData.length > 60) chartRegenData.shift();
    speedRegenChart.data.datasets[0].data = chartSpeedData;
    speedRegenChart.data.datasets[1].data = chartRegenData;
    speedRegenChart.update('none');
  }

  if (Number.isFinite(d.batteryV)) {
    document.getElementById('batteryVal').textContent = d.batteryV.toFixed(1) + 'В';
    const bp = Math.max(0, Math.min(100, (d.batteryV / 120) * 100));
    document.getElementById('batteryBar').style.width = bp.toFixed(1) + '%';
  }

  if (Number.isFinite(d.pressure)) {
    document.getElementById('pressureVal').textContent = d.pressure.toFixed(2) + ' атм';
    const pp = Math.max(0, Math.min(100, (d.pressure / 6.5) * 100));
    document.getElementById('pressureBar').style.width = pp.toFixed(1) + '%';
  }

  if (Number.isFinite(d.healthIndex)) document.getElementById('healthIdx').textContent = Math.round(d.healthIndex);
  if (d.healthGrade) document.getElementById('healthGrade').textContent = d.healthGrade;

  if (Number.isFinite(d.transformerTemp)) {
    document.getElementById('transformerTemp').textContent = d.transformerTemp.toFixed(1) + '°C';
    const tp = Math.max(0, Math.min(100, (d.transformerTemp / 120) * 100));
    document.getElementById('transformerBar').style.width = tp.toFixed(1) + '%';
  }

  if (typeof d.pantographUp === 'boolean') {
    document.getElementById('pantographState').textContent = d.pantographUp ? 'ПОДНЯТ' : 'ОПУЩЕН';
    document.getElementById('pantographBar').style.width = d.pantographUp ? '100%' : '0%';
  }

  if (d.tdCurrents.length >= 4) {
    document.getElementById('td1cur').textContent = Number(d.tdCurrents[0]).toFixed(1) + 'А';
    document.getElementById('td2cur').textContent = Number(d.tdCurrents[1]).toFixed(1) + 'А';
    document.getElementById('td3cur').textContent = Number(d.tdCurrents[2]).toFixed(1) + 'А';
    document.getElementById('td4cur').textContent = Number(d.tdCurrents[3]).toFixed(1) + 'А';
  }
  if (d.tdTemps.length >= 4) {
    document.getElementById('td1temp').textContent = Number(d.tdTemps[0]).toFixed(1) + '°';
    document.getElementById('td4temp').textContent = Number(d.tdTemps[3]).toFixed(1) + '°';
  }

  const bpStatus = String(d.sensors?.BRAKE_PRESSURE?.status || '').toUpperCase();
  const ohStatus = String(d.sensors?.OVERHEAT?.status || '').toUpperCase();
  const vStatus = String(d.sensors?.VOLTAGE?.status || '').toUpperCase();
  document.getElementById('pressureStatus').textContent = bpStatus || 'OK';

  partStatus['part-brakes'] = bpStatus === 'CRIT' ? 'crit' : bpStatus === 'WARN' ? 'warn' : 'ok';
  partStatus['part-transformer'] = ohStatus === 'CRIT' ? 'crit' : (ohStatus === 'WARN' || vStatus === 'WARN') ? 'warn' : 'ok';
  partStatus['part-pantograph'] = d.pantographUp === false ? 'warn' : 'ok';
  partStatus['part-cooling'] = Number.isFinite(d.transformerTemp) && d.transformerTemp > 85 ? 'warn' : 'ok';
  partStatus['part-motors'] = d.tdTemps.some((t) => Number(t) > 95) ? 'crit' : d.tdTemps.some((t) => Number(t) > 85) ? 'warn' : 'ok';
  partStatus['part-regen'] = Number.isFinite(regen) && regen > 0 ? 'ok' : 'warn';
  applyDiagramStatus();
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

// ===== CHARTS =====
const labels=Array.from({length:60},(_,i)=>i);
const c1=document.getElementById('spdChart').getContext('2d');
speedRegenChart = new Chart(c1,{type:'line',data:{labels,datasets:[
  {data:chartSpeedData,borderColor:'#a78bfa',borderWidth:1.5,pointRadius:0,tension:.3,fill:false,yAxisID:'y'},
  {data:chartRegenData,borderColor:'#34d399',borderWidth:1.5,pointRadius:0,tension:.3,fill:true,backgroundColor:'rgba(52,211,153,0.08)',yAxisID:'y2'}
]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
scales:{x:{display:false},y:{position:'left',min:0,max:220,ticks:{color:'#334155',font:{size:8},stepSize:20},grid:{color:'rgba(255,255,255,0.04)'},border:{display:false}},
y2:{position:'right',min:0,max:5,ticks:{color:'#334155',font:{size:8},stepSize:2.5},grid:{display:false},border:{display:false}}},animation:{duration:0}}});

const tdL=Array.from({length:20},(_,i)=>i);
const td1=[410,411,412,412,413,412,412,413,412,412,412,412,413,412,412,412,412,412,412,412];
const td4=[425,427,428,429,430,430,431,431,430,431,431,431,431,430,431,431,431,431,431,431];
const c2=document.getElementById('tdChart').getContext('2d');
new Chart(c2,{type:'line',data:{labels:tdL,datasets:[
  {data:td1,borderColor:'#4ade80',borderWidth:1.5,pointRadius:0,tension:.3,fill:false},
  {data:td4,borderColor:'#facc15',borderWidth:1.5,pointRadius:0,tension:.3,fill:false}
]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{enabled:false}},
scales:{x:{display:false},y:{min:390,max:450,ticks:{color:'#334155',font:{size:8},stepSize:20},grid:{color:'rgba(255,255,255,0.04)'},border:{display:false}}},animation:{duration:0}}});
