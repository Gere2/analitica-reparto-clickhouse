'use strict';
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat('es-ES');
const money=value=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(Number(value||0)/100);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock=value=>value?new Date(value.replace(' ','T')+'Z').toLocaleTimeString('es-ES'): '—';
const states={created:'Creado',preparing:'Preparando',picked_up:'Recogido',en_route:'En reparto',delivered:'Entregado',cancelled:'Cancelado'};
let selected='',lastData=null,lastSimulation={},refreshTimer=null,fetching=false,controlling=false,manualEvent=null;
let navigationFetching=false,navigationAt=0,navigationOrigin='';
const session=crypto.randomUUID();
const readOnly=Boolean(document.querySelector('meta[name="atlas-readonly"]'));
async function request(path,body){
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch(path,{signal:controller.signal,cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
    const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;
  }finally{clearTimeout(timeout);}
}
function project(lat,lon){return [28+(Number(lon)+3.718)/.037*744,450-(Number(lat)-40.400)/.030*420];}
function svgNode(tag,attrs){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value));return node;}
function showError(message){$('error').hidden=!message;$('error').textContent=message;}
function buttons(){ if(readOnly)return; $('start').disabled=controlling||lastSimulation.running;$('stop').disabled=controlling||!lastSimulation.running;$('fleet').disabled=controlling||lastSimulation.running; }
function selectCourier(id){selected=id;$('courier').value=id;if(lastData)renderMap(lastData);}
function renderMap(data){
  const couriers=data.couriers||[];
  if(!couriers.some(row=>row.courier_id===selected))selected=couriers[0]?.courier_id||'';
  const previous=$('courier').value;
  if($('courier').options.length!==couriers.length||!couriers.some(r=>r.courier_id===previous)){
    $('courier').replaceChildren(...couriers.map((row,i)=>{const option=document.createElement('option');option.value=row.courier_id;option.textContent=`Repartidor ${String(i+1).padStart(2,'0')} · ${row.courier_id.slice(0,8)}`;return option;}));
  }
  $('courier').value=selected;
  $('markers').replaceChildren();
  couriers.forEach((row,i)=>{
    const [x,y]=project(row.latitude,row.longitude);
    const group=svgNode('g',{});
    const dot=svgNode('circle',{cx:x,cy:y,r:row.courier_id===selected?13:10,class:`marker ${row.courier_id===selected?'selected':''} ${Number(row.age_ms)>10000?'stale':''}`});
    const title=svgNode('title',{});title.textContent=`Repartidor ${i+1}: ${row.latitude}, ${row.longitude}`;dot.append(title);
    dot.addEventListener('click',()=>selectCourier(row.courier_id));
    const label=svgNode('text',{x,y:y+3.5,'text-anchor':'middle',class:'marker-label'});label.textContent=i+1;
    group.append(dot,label);$('markers').append(group);
  });
  $('map-empty').setAttribute('visibility',couriers.length?'hidden':'visible');
  const row=couriers.find(r=>r.courier_id===selected);
  $('destinations').replaceChildren();$('route').setAttribute('points','');
  if(!row){$('freshness').textContent='Sin posiciones';return;}
  const order=(data.orders||[]).find(o=>o.order_id===row.order_id);
  const age=Math.max(0,(Date.now()-Date.parse(row.event_time.replace(' ','T')+'Z'))/1000);
  $('freshness').textContent=`${couriers.length} repartidores · posición seleccionada: hace ${age.toFixed(1)} s`;
  $('courier-detail').innerHTML=[['Pedido',row.order_id.slice(0,8)],['Estado',states[order?.status]||'Esperando estado'],
    ['Latitud',Number(row.latitude).toFixed(6)],['Longitud',Number(row.longitude).toFixed(6)],
    ['Velocidad simulada',`${Number(row.speed_kmh).toFixed(1)} km/h`],['Precisión simulada',`${row.accuracy_m} m`],
    ['Hora del evento',clock(row.event_time)],['Antigüedad',`${age.toFixed(1)} s`],
    ['Hasta recibir en API',`${Math.max(0,Number(row.receipt_delay_ms))} ms`]]
    .map(([key,value])=>`<dt>${escapeHTML(key)}</dt><dd>${escapeHTML(value)}</dd>`).join('');
  if(order){
    for(const [lat,lon,color,label] of [[order.pickup_lat,order.pickup_lon,'#24553d','Recogida ficticia'],[order.dropoff_lat,order.dropoff_lon,'#a96224','Entrega ficticia']]){
      const [x,y]=project(lat,lon);const dot=svgNode('rect',{x:x-5,y:y-5,width:10,height:10,fill:color});const title=svgNode('title',{});title.textContent=label;dot.append(title);$('destinations').append(dot);
    }
  }
  const selectedAtRequest=selected,runAtRequest=data.run_id;
  request(`/api/track?run_id=${encodeURIComponent(data.run_id)}&courier_id=${encodeURIComponent(selected)}`).then(history=>{
    if(selected!==selectedAtRequest||lastData?.run_id!==runAtRequest)return;
    const points=history.rows.filter(p=>p.order_id===row.order_id).map(p=>project(p.latitude,p.longitude).join(','));
    $('route').setAttribute('points',points.join(' '));
    $('rate-note').textContent='El gráfico se consulta desde el histórico GPS en ClickHouse.';
  }).catch(()=>{$('rate-note').textContent='No se pudo consultar el recorrido. Se reintentará en la siguiente actualización.';});
}
function renderOperations(data){
  lastData=data;const m=data.metrics||{};
  for(const key of ['active','delivered','cancelled','late'])$(key).textContent=fmt.format(Number(m[key]||0));
  $('amount').textContent=money(m.delivered_amount_minor);
  $('order-count').textContent=`${fmt.format(Number(m.orders||0))} pedidos${data.truncated?' · lista limitada a 200':''}`;
  $('orders-body').innerHTML=(data.orders||[]).map(row=>`<tr><td>${escapeHTML(row.order_id.slice(0,8))}</td><td>${escapeHTML(row.restaurant_id.replace('fictional-madrid-','Madrid · local '))}</td><td><span class="badge ${escapeHTML(row.status)}">${escapeHTML(states[row.status]||row.status)}</span></td><td>${money(row.amount_minor)}</td><td>${clock(row.order_created_at)}</td><td>${clock(row.promised_delivery_at)}</td></tr>`).join('')||'<tr><td colspan="6">Sin pedidos en esta ejecución. Inicia la simulación.</td></tr>';
  const rate=data.positions_by_5s||[];const max=Math.max(1,...rate.map(r=>Number(r.positions)));
  $('rate').replaceChildren(...rate.map(row=>{const bar=document.createElement('div');bar.style.height=`${Number(row.positions)/max*100}%`;bar.title=`${clock(row.bucket)} · ${row.positions} posiciones`;return bar;}));
  renderMap(data);
}
function renderNavigation(data){
  const totals={};(data.rows||[]).forEach(row=>totals[row.event_type]=(totals[row.event_type]||0)+Number(row.events));
  const steps=[['search','Búsquedas'],['restaurant_opened','Restaurantes'],['product_opened','Productos'],['cart_added','Carritos'],['order_submitted','Pedidos enviados']];
  const max=Math.max(1,...Object.values(totals));
  $('actions').innerHTML=steps.map(([key,label])=>`<div><span>${label}</span><strong>${fmt.format(totals[key]||0)}</strong><div class="action-track"><i style="width:${(totals[key]||0)/max*100}%"></i></div></div>`).join('');
  $('navigation-count').textContent=`${fmt.format(data.events)} eventos de Madrid · ${$('origin').selectedOptions[0].textContent.toLowerCase()} · todo el histórico Atlas${data.truncated?' · solo primeros grupos representados':''} · consulta ${new Date().toLocaleTimeString('es-ES')} (intervalo 10 s).`;
}
async function loadNavigation(force=false){
  const origin=$('origin').value;
  if(navigationFetching||(!force&&navigationOrigin===origin&&Date.now()-navigationAt<10000))return;
  navigationFetching=true;
  try{const data=await request(`/api/summary?city_id=madrid&source_kind=${origin}`);if(origin===$('origin').value){renderNavigation(data);navigationAt=Date.now();navigationOrigin=origin;}}
  catch(error){$('navigation-count').textContent=`Consulta de navegación fallida: ${error.message}. Se reintentará.`;}
  finally{navigationFetching=false;}
}
async function poll(){
  if(fetching)return;fetching=true;
  try{
    lastSimulation=await request('/api/simulation');buttons();
    const [data,queue]=await Promise.all([request('/api/operations'),request('/api/status')]);
    renderOperations(data);$('pending').textContent=fmt.format(queue.pending);loadNavigation();
    const state=lastSimulation.error?`Simulación detenida: ${lastSimulation.error}`:lastSimulation.running?`Simulación activa · ${lastSimulation.fleet} repartidores · intervalo solicitado: ${lastSimulation.interval_seconds} s`:'Simulación parada; el histórico se conserva';
    $('status').textContent=`${state}. Última consulta: ${new Date().toLocaleTimeString('es-ES')}${lastSimulation.run_id?` · ejecución ${lastSimulation.run_id.slice(0,8)}`:''}.`;
    showError(queue.publisher_error?`La publicación está reintentando: ${queue.publisher_error}. Los eventos aceptados siguen en cola.`:lastSimulation.error||'');
  }catch(error){showError(`No se pudo actualizar: ${error.message}. Se conservan los datos anteriores y se reintentará.`);$('freshness').textContent='Consulta fallida · posiciones anteriores';}
  finally{fetching=false;clearTimeout(refreshTimer);refreshTimer=setTimeout(poll,2000);}
}
async function control(action){
  controlling=true;buttons();
  try{lastSimulation=await request(`/api/simulation/${action}`,action==='start'?{fleet:Number($('fleet').value),interval:2,seed:42}:{});showError('');}
  catch(error){showError(error.message);}
  finally{controlling=false;buttons();await poll();}
}
if(!readOnly){$('start').addEventListener('click',()=>control('start'));$('stop').addEventListener('click',()=>control('stop'));}
$('courier').addEventListener('change',()=>selectCourier($('courier').value));
$('origin').addEventListener('change',()=>loadNavigation(true));
$('manual').addEventListener('click',async()=>{
  $('manual').disabled=true;
  manualEvent=manualEvent||{schema_version:1,event_id:crypto.randomUUID(),session_id:session,event_time:new Date().toISOString(),event_type:'search',section:'search',city_id:'madrid',source:'atlas-dashboard',source_kind:'demo_live'};
  try{const data=await request('/api/events',{events:[manualEvent]});$('manual-status').textContent=data.accepted?'Búsqueda recibida en cola; pendiente de publicación.':'Búsqueda ya recibida; reintento reconocido.';manualEvent=null;$('manual').textContent='Registrar una búsqueda manual';}
  catch(error){$('manual-status').textContent=`No se confirmó el envío: ${error.message}`;$('manual').textContent='Reintentar la misma búsqueda';}
  finally{$('manual').disabled=false;}
});
const uses={otto_archive:'Eventos públicos OTTO',rees46_events:'Eventos públicos REES46',eleme_samples:'Muestras públicas Ele.me',glovo_products:'Catálogo publicado; sin clics',orders:'Pedidos históricos TRD / Meituan',clicks:'Secuencias históricas TRD / Meituan',restaurants:'Restaurantes históricos TRD',foods:'Productos históricos TRD',order_items:'Líneas de pedidos históricos',otto_scale_benchmark:'Filas derivadas para estrés',otto_replay:'Reproducción histórica',app_events:'Navegación propia, origen etiquetado',courier_positions:'GPS sintético',order_events:'Estados de pedidos sintéticos'};
async function loadContext(){
  const results=await Promise.allSettled([request('/api/inventory'),request('/api/catalog')]);
  if(results[0].status==='fulfilled')$('inventory-body').innerHTML=results[0].value.rows.filter(r=>uses[r.name]).map(row=>`<tr><td>${escapeHTML(row.database+'.'+row.name)}</td><td>${fmt.format(Number(row.total_rows||0))}</td><td>${escapeHTML(row.disk)}</td><td>${escapeHTML(uses[row.name])}</td></tr>`).join('');
  else $('inventory-body').innerHTML='<tr><td colspan="4">No se pudo consultar el inventario. Recarga para reintentar.</td></tr>';
  if(results[1].status==='fulfilled'){
    const catalog=results[1].value;$('catalog-note').textContent=catalog.meaning+' Las posiciones simuladas no pertenecen a estos negocios.';
    $('catalog').innerHTML=catalog.rows.slice(0,12).map(row=>`<article><strong>${escapeHTML(row.product_name)}</strong><p>${escapeHTML(row.store_name)} · ${escapeHTML(row.collection_section)}</p></article>`).join('')||'<p class="empty">La simulación funciona sin este catálogo. Está disponible en el laboratorio de Jere.</p>';
  }else $('catalog').innerHTML='<p class="empty">El catálogo no está disponible. Recarga para reintentar; la flota sigue funcionando.</p>';
}
poll();loadContext();
document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
