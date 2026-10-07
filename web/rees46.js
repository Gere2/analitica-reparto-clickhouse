const el = id => document.getElementById(id);
const fmt = value => new Intl.NumberFormat('es-ES').format(Number(value || 0));
const escapeText = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const monthLabels = {'201910':'Oct 19','201911':'Nov 19','201912':'Dic 19','202001':'Ene 20','202002':'Feb 20','202003':'Mar 20','202004':'Abr 20'};

function paint(data) {
  const m = data.metrics;
  for (const [id,key] of [['k-events','events'],['k-views','views'],['k-carts','carts'],['k-purchases','purchases'],['k-users','users_approx']]) el(id).textContent = fmt(m[key]);
  const byMonth = {};
  for (const row of data.monthly) byMonth[row.month] = (byMonth[row.month] || 0) + Number(row.events);
  const max = Math.max(1,...Object.values(byMonth));
  el('monthly-chart').innerHTML = Object.entries(monthLabels).map(([key,label]) => `<div class="market-month"><strong>${fmt(byMonth[key] || 0)}</strong><i style="height:${Math.max(3,(byMonth[key] || 0)/max*185)}px"></i><span>${label}</span></div>`).join('');
  const actions = [['Vistas','views'],['Carritos','carts'],['Retiradas','removals'],['Compras','purchases']];
  el('action-chart').innerHTML = actions.map(([label,key]) => `<div class="bar-row"><span class="bar-name">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${m.events ? Number(m[key])/Number(m.events)*100 : 0}%"></div></div><span class="bar-value">${fmt(m[key])}</span></div>`).join('');
  el('category-rows').innerHTML = data.categories.map(row => `<tr><td>${escapeText(row.category)}</td><td>${fmt(row.views)}</td><td>${fmt(row.carts)}</td><td>${fmt(row.purchases)}</td></tr>`).join('');
  const brandMax = Math.max(1,...data.brands.map(row => Number(row.events)));
  el('brand-chart').innerHTML = data.brands.map(row => `<div class="bar-row"><span class="bar-name">${escapeText(row.brand)}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(row.events)/brandMax*100}%"></div></div><span class="bar-value">${fmt(row.events)}</span></div>`).join('');
  el('status').classList.remove('error');
  el('status').textContent = `${fmt(m.events)} eventos consultados · ${data.month === 'ALL' ? 'todos los meses' : monthLabels[data.month]}`;
}

async function load() {
  el('status').textContent = 'Agrupando datos en ClickHouse…';
  try {
    const response = await fetch(`/api/rees46?month=${encodeURIComponent(el('month').value)}`,{cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Consulta fallida');
    paint(data);
  } catch (error) { el('status').textContent = error.message; el('status').classList.add('error'); }
}
el('filters').addEventListener('submit', event => {event.preventDefault();load();});
load();
