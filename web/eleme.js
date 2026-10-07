const el = id => document.getElementById(id);
const fmt = value => new Intl.NumberFormat('es-ES').format(Number(value || 0));
const esc = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mealLabels={breakfast:'Desayuno',lunch:'Comida',tea:'Merienda',dinner:'Cena',night:'Noche / madrugada'};
function paint(data){
  const m=data.metrics;
  for(const [id,key] of [['k-samples','samples'],['k-clicks','clicks'],['k-users','users_approx']])el(id).textContent=fmt(m[key]);
  el('k-positive').textContent=m.positive_pct===null?'—':new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(m.positive_pct)+' %';
  el('loaded-total').textContent=fmt(data.loaded_total);
  el('empty').hidden=!data.empty;
  if(data.empty&&data.staging_rows){
    el('empty-label').textContent='VALIDANDO EL PRIMER ARCHIVO';
    el('empty-title').textContent='El ZIP está descargado. La carga está en curso.';
    el('empty-detail').textContent=fmt(data.staging_rows)+' filas en staging. Se publicarán al validar el archivo completo y comprobar el recuento; estas filas todavía no se suman a las muestras cargadas del dashboard.';
  }else{
    el('empty-label').textContent='DESCARGA PENDIENTE';
    el('empty-title').textContent='La conexión está preparada. Los archivos aún no están cargados.';
    el('empty-detail').textContent='Descarga un ZIP oficial de Tianchi, comprueba su formato y cárgalo con el importador. Los recuentos de abajo proceden de nuestra base de datos.';
  }
  const max=Math.max(1,...data.days.map(row=>Number(row.samples)));
  el('day-chart').innerHTML=data.days.length?data.days.map(row=>`<div class="bar-row"><span class="bar-name">D${row.day}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(row.samples)/max*100}%"></div></div><span class="bar-value">${fmt(row.samples)}</span></div>`).join(''):'<p class="empty-chart">Sin días importados todavía.</p>';
  const hours=Object.fromEntries(data.hours.map(row=>[row.hour,row]));
  el('hour-chart').innerHTML=data.hours.length?Array.from({length:24},(_,hour)=>`<div class="hour-cell"><span>${String(hour).padStart(2,'0')}:00</span><b>${fmt(hours[hour]?.samples)}</b></div>`).join(''):'<p class="empty-chart">Sin muestras para este filtro.</p>';
  el('city-rows').innerHTML=data.cities.length?data.cities.map(row=>`<tr><td>${esc(row.city)}</td><td>${fmt(row.samples)}</td><td>${fmt(row.clicks)}</td></tr>`).join(''):'<tr><td colspan="3">Sin muestras para este filtro.</td></tr>';
  el('meal-rows').innerHTML=data.meals?.length?data.meals.map(row=>`<tr><td>${esc(mealLabels[row.period]||row.period)}</td><td>${fmt(row.samples)}</td><td>${fmt(row.clicks)}</td><td>${new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(100*Number(row.clicks)/Number(row.samples))} %</td></tr>`).join(''):'<tr><td colspan="4">Sin muestras para este filtro.</td></tr>';
  el('file-rows').innerHTML=data.files.length?data.files.map(row=>`<tr><td>${esc(row.file)}</td><td>D${row.day}</td><td>${fmt(row.samples)}</td></tr>`).join(''):'<tr><td colspan="3">Ningún archivo publicado en ClickHouse.</td></tr>';
  el('status').classList.remove('error');
  el('status').textContent=data.empty?(data.staging_rows?`Ingesta en curso · ${fmt(data.staging_rows)} filas en staging · 0 publicadas`:'ClickHouse conectado · 0 muestras Ele.me cargadas · descarga pendiente'):`${fmt(m.samples)} muestras consultadas · ${data.day==='ALL'?'todos los días cargados':'D'+data.day} · ${fmt(m.clicks)} etiquetas positivas`;
}
async function load(){
  el('status').textContent='Consultando muestras en ClickHouse…';
  try{const response=await fetch('/api/eleme?day='+encodeURIComponent(el('day').value),{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'Consulta fallida');paint(data)}
  catch(error){el('status').textContent=error.message;el('status').classList.add('error')}
}
el('filters').addEventListener('submit',event=>{event.preventDefault();load()});
load();
setInterval(load,30000);
