const el = id => document.getElementById(id);
const fmt = value => new Intl.NumberFormat('es-ES').format(value || 0);
const escapeText = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let loading = false;

function paint(data) {
  const archive = data.archive;
  el('k-events').textContent = fmt(archive.events);
  el('k-clicks').textContent = fmt(archive.clicks);
  el('k-carts').textContent = fmt(archive.carts);
  el('k-orders').textContent = fmt(archive.orders);
  const stream = data.replay_30s;
  el('s-events').textContent = fmt(stream.events);
  el('s-sessions').textContent = fmt(stream.sessions);
  el('s-total').textContent = fmt(data.replayed_total);
  el('rate').textContent = `${fmt(Math.round(stream.events / 30))} eventos/s · media 30 s`;
  el('live-count').textContent = fmt(data.live_clicks);
  const timeline = data.timeline;
  const max = Math.max(1, ...timeline.map(row => Number(row.clicks) + Number(row.carts) + Number(row.orders)));
  el('timeline').innerHTML = timeline.length ? timeline.map(row => {
    const bars = [['clicks','#84b98c'],['carts','#e8b47a'],['orders','#486f94']].map(([kind,color]) =>
      `<span title="${escapeText(row.second)} · ${kind}: ${fmt(row[kind])}" style="height:${Math.max(2, Number(row[kind]) / max * 155)}px;background:${color}"></span>`).join('');
    return `<div class="tick">${bars}</div>`;
  }).join('') : '<p class="panel-sub">Esperando al reproductor de eventos…</p>';
  const types = [['Clics','clicks','#84b98c'],['Carritos','carts','#e8b47a'],['Pedidos','orders','#486f94']];
  el('funnel').innerHTML = types.map(([label,key,color]) => `<div class="funnel-row"><span>${label}</span><div class="funnel-bar"><i style="width:${stream.events ? Number(stream[key]) / Number(stream.events) * 100 : 0}%;background:${color}"></i></div><strong>${fmt(stream[key])}</strong></div>`).join('');
  const topMax = Math.max(1, ...data.top.map(row => Number(row.events)));
  el('top-products').innerHTML = data.top.length ? data.top.map(row => `<div class="bar-row"><span class="bar-name">#${fmt(row.article_id)}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(row.events) / topMax * 100}%"></div></div><span class="bar-value">${fmt(row.events)}</span></div>`).join('') : '<p class="panel-sub">Aún no hay eventos reproducidos.</p>';
  el('recent-live').innerHTML = data.recent_live.map(row => `<li>${escapeText(row.section)} · ${escapeText(row.action)} <time>${escapeText(row.clicked_at)}</time></li>`).join('');
  el('status').textContent = `${fmt(archive.events)} filas cargadas · actualización cada 2 s · ${stream.events ? 'reproductor activo' : 'sin eventos reproducidos en los últimos 30 s'}`;
}

async function refresh() {
  if (loading) return;
  loading = true;
  try {
    const response = await fetch('/api/otto', {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Error de consulta');
    paint(data);
    el('status').classList.remove('error');
  } catch (error) {
    el('status').textContent = `No se pudo consultar ClickHouse: ${error.message}`;
    el('status').classList.add('error');
  } finally { loading = false; }
}

document.querySelectorAll('[data-section]').forEach(button => button.addEventListener('click', async () => {
  button.disabled = true;
  try {
    const response = await fetch('/api/live-click', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:button.dataset.section,action:button.dataset.action})});
    if (!response.ok) throw new Error((await response.json()).error || 'No se guardó el clic');
    await refresh();
  } catch (error) { el('status').textContent = error.message; el('status').classList.add('error'); }
  finally { button.disabled = false; }
}));

refresh();
setInterval(refresh, 2000);
