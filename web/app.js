const nf = new Intl.NumberFormat('es-ES');
const el = id => document.getElementById(id);
const fmt = n => nf.format(Number(n || 0));

function barRow(name, value, max, color) {
  const row = document.createElement('div'); row.className = 'bar-row';
  const label = document.createElement('span'); label.className = 'bar-name'; label.textContent = name;
  const track = document.createElement('div'); track.className = 'bar-track';
  const fill = document.createElement('div'); fill.className = 'bar-fill';
  fill.style.width = `${Math.max(1, Number(value) / Math.max(1, max) * 100)}%`;
  if (color) fill.style.background = color;
  track.append(fill);
  const number = document.createElement('span'); number.className = 'bar-value'; number.textContent = fmt(value);
  row.append(label, track, number);
  return row;
}

function renderDaily(days) {
  const host = el('daily-chart'); host.replaceChildren();
  const maxOrders = Math.max(1, ...days.map(d => Number(d.orders)));
  const maxClicks = Math.max(1, ...days.map(d => Number(d.clicks)));
  days.forEach((day, i) => {
    const group = document.createElement('div'); group.className = 'day-group';
    group.title = `${day.day}: ${fmt(day.orders)} pedidos · ${fmt(day.clicks)} clics`;
    [['bar-orders', day.orders, maxOrders], ['bar-clicks', day.clicks, maxClicks]].forEach(([className, value, max]) => {
      const bar = document.createElement('div'); bar.className = `bar ${className}`;
      bar.style.height = `${Math.max(1, Number(value) / max * 100)}%`; group.append(bar);
    });
    if (days.length <= 8 || i % 3 === 0 || i === days.length - 1) {
      const label = document.createElement('span'); label.className = 'day-label'; label.textContent = day.day.slice(-2); group.append(label);
    }
    host.append(group);
  });
}

function renderHours(hours) {
  const host = el('hour-chart'); host.replaceChildren();
  const byHour = new Map(hours.map(row => [Number(row.hour), Number(row.orders)]));
  const max = Math.max(1, ...byHour.values());
  for (let hour = 0; hour < 24; hour++) {
    const wrap = document.createElement('div'); wrap.className = 'hour-bar-wrap';
    const count = byHour.get(hour) || 0; wrap.title = `${hour}:00 · ${fmt(count)} pedidos`;
    const bar = document.createElement('div'); bar.className = 'hour-bar';
    bar.style.height = `${Math.max(1, count / max * 100)}%`; wrap.append(bar);
    if (hour % 4 === 0) { const label = document.createElement('span'); label.className = 'hour-label'; label.textContent = String(hour).padStart(2, '0'); wrap.append(label); }
    host.append(wrap);
  }
}

function renderBars(id, rows, getLabel, color) {
  const host = el(id); host.replaceChildren();
  const max = Math.max(1, ...rows.map(row => Number(row.orders)));
  rows.forEach(row => host.append(barRow(getLabel(row), row.orders, max, color)));
}

function renderTable(rows) {
  const body = el('top-table'); body.replaceChildren();
  rows.forEach(row => {
    const tr = document.createElement('tr');
    [`#${row.restaurant_id}`, `Categoría ${row.category}`, row.score == null ? '—' : Number(row.score).toFixed(1), fmt(row.orders), fmt(row.clicks)].forEach(value => {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    });
    body.append(tr);
  });
}

function render(data) {
  el('k-orders').textContent = fmt(data.metrics.orders);
  el('k-clicks').textContent = fmt(data.metrics.clicks);
  el('k-users').textContent = fmt(data.metrics.users);
  el('k-ratio').textContent = new Intl.NumberFormat('es-ES', {maximumFractionDigits: 2}).format(data.metrics.clicks_per_order);
  el('match-value').textContent = `${data.metrics.last_click_match_pct}%`;
  renderDaily(data.daily); renderHours(data.hours);
  renderBars('depth-chart', data.depth, row => `${row.bucket} clics`, '#80b991');
  renderBars('price-chart', data.price_bands, row => row.price_band, '#e7aa78');
  renderTable(data.top);
}

async function load() {
  const status = el('status'); status.classList.remove('error'); status.textContent = 'Consultando millones de registros en ClickHouse…';
  const params = new URLSearchParams({from: el('from').value, to: el('to').value});
  try {
    const response = await fetch(`/api/dashboard?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo cargar el dashboard');
    render(data);
    status.textContent = `Periodo ${el('from').value} → ${el('to').value} · ${fmt(data.metrics.orders)} pedidos analizados`;
  } catch (error) { status.textContent = error.message; status.classList.add('error'); }
}

el('filters').addEventListener('submit', event => { event.preventDefault(); load(); });
load();
