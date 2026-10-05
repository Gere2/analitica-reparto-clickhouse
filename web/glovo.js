const nf = new Intl.NumberFormat('es-ES');
const el = id => document.getElementById(id);
const fmt = n => nf.format(Number(n || 0));

function barRow(name, value, max, color) {
  const row = document.createElement('div'); row.className = 'bar-row';
  const label = document.createElement('span'); label.className = 'bar-name'; label.textContent = name; label.title = name;
  const track = document.createElement('div'); track.className = 'bar-track';
  const fill = document.createElement('div'); fill.className = 'bar-fill';
  fill.style.width = `${Math.max(1, Number(value) / Math.max(1, max) * 100)}%`;
  fill.style.background = color; track.append(fill);
  const number = document.createElement('span'); number.className = 'bar-value'; number.textContent = fmt(value);
  row.append(label, track, number); return row;
}

function renderBars(id, rows, label, color) {
  const host = el(id); host.replaceChildren();
  const max = Math.max(1, ...rows.map(row => Number(row.products)));
  rows.forEach(row => host.append(barRow(label(row), row.products, max, color)));
  if (!rows.length) host.textContent = 'No hay datos para este filtro.';
}

function updateSelect(select, rows, valueKey, label, selected) {
  select.replaceChildren(new Option(select.id === 'country' ? 'Todos los países' : 'Todas las ciudades', select.id === 'country' ? 'ALL' : ''));
  rows.forEach(row => select.add(new Option(label(row), row[valueKey])));
  select.value = selected;
}

function render(data) {
  const m = data.metrics;
  el('g-products').textContent = fmt(m.products);
  el('g-stores').textContent = fmt(m.stores);
  el('g-cities').textContent = fmt(m.cities);
  el('g-description').textContent = `${nf.format(m.description_pct)} %`;
  renderBars('g-city-chart', data.cities, row => row.city || 'Sin código', '#80b991');
  renderBars('g-section-chart', data.sections, row => row.section, '#e7aa78');
  const tbody = el('g-store-table'); tbody.replaceChildren();
  data.stores.forEach(row => {
    const tr = document.createElement('tr');
    [row.store, fmt(row.products), fmt(row.cities), fmt(row.sections)].forEach(value => {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    });
    tbody.append(tr);
  });
  updateSelect(el('country'), data.countries, 'country', row => `${row.country} · ${fmt(row.products)}`, data.selection.country);
  updateSelect(el('city'), data.city_options, 'city', row => `${row.city || 'Sin código'} · ${fmt(row.products)}`, data.selection.city);
  el('city').disabled = data.selection.country === 'ALL';
}

async function load() {
  const status = el('glovo-status'); status.classList.remove('error');
  status.textContent = 'Consultando el catálogo de Glovo en ClickHouse…';
  const params = new URLSearchParams({country: el('country').value, city: el('city').value});
  try {
    const response = await fetch(`/api/glovo?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo cargar el catálogo');
    render(data);
    const place = data.selection.country === 'ALL' ? 'todos los países' : data.selection.city || data.selection.country;
    status.textContent = `${fmt(data.metrics.products)} productos · ${place} · fuente Glovo FooDI-ML`;
  } catch (error) { status.textContent = error.message; status.classList.add('error'); }
}

el('glovo-filters').addEventListener('submit', event => { event.preventDefault(); load(); });
el('country').addEventListener('change', () => { el('city').value = ''; load(); });
el('city').addEventListener('change', load);
load();
