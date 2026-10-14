'use strict';
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat('es-ES');
const money=value=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(Number(value||0)/100);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock=value=>value?new Date(value.replace(' ','T')+'Z').toLocaleTimeString('es-ES'): '—';
const states={created:'Creado',preparing:'Preparando',picked_up:'Recogido',en_route:'En reparto',delivered:'Entregado',cancelled:'Cancelado'};
let selected='',lastData=null,lastSimulation={},refreshTimer=null,fetching=false,controlling=false,manualEvent=null;
let navigationFetching=false,navigationAt=0,navigationOrigin='';
let trackFetching=false,showAllCustomers=false;
const decisionLabel=mode=>({ollama:'IA local',traffic:'Simulador de tráfico',policy:'Política de prueba',system:'Sistema'}[mode]||mode);
const customerActions={session_started:'Empieza una sesión',search:'Busca comida',open_restaurant:'Compara restaurante',open_product:'Abre un producto',add_to_cart:'Añade al carrito',remove_from_cart:'Quita del carrito',checkout:'Confirma compra',abandon:'Abandona la sesión',delivery_completed:'Recibe su pedido'};
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
function buttons(){ if(readOnly)return; if(lastSimulation.running){$('fleet').value=String(lastSimulation.fleet);$('customer-count').value=String(lastSimulation.customers||3);$('agent-mode').value=lastSimulation.mode==='customers'?lastSimulation.agent_mode:'legacy';} $('start').disabled=controlling||lastSimulation.running;$('stop').disabled=controlling||!lastSimulation.running;for(const id of ['fleet','agent-mode','customer-count'])$(id).disabled=controlling||lastSimulation.running; }
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
    const dot=svgNode('circle',{cx:x,cy:y,r:row.courier_id===selected?11:couriers.length>24?5:10,class:`marker ${row.courier_id===selected?'selected':''} ${Number(row.age_ms)>10000?'stale':''}`});
    const title=svgNode('title',{});title.textContent=`Repartidor ${i+1}: ${row.latitude}, ${row.longitude}`;dot.append(title);
    dot.addEventListener('click',()=>selectCourier(row.courier_id));
    const label=svgNode('text',{x,y:y+3.5,'text-anchor':'middle',class:'marker-label'});label.textContent=i+1;
    group.append(dot);if(couriers.length<=24||row.courier_id===selected)group.append(label);$('markers').append(group);
  });
  $('map-empty').setAttribute('visibility',couriers.length?'hidden':'visible');
  const row=couriers.find(r=>r.courier_id===selected);
  $('destinations').replaceChildren();$('route').setAttribute('points','');
  if(!row){$('freshness').textContent='Sin posiciones';return;}
  const order=(data.orders||[]).find(o=>o.order_id===row.order_id);
  const customer=(data.customers||[]).find(c=>c.customer_id===order?.customer_id);
  const age=Math.max(0,(Date.now()-Date.parse(row.event_time.replace(' ','T')+'Z'))/1000);
  $('freshness').textContent=`${couriers.length} repartidores · posición seleccionada: hace ${age.toFixed(1)} s`;
  $('courier-detail').innerHTML=[['Pedido',row.order_id.startsWith('00000000-')?'Sin pedido asignado':row.order_id.slice(0,8)],['Estado',states[order?.status]||'Disponible'],
    ...(order?.customer_id?[['Cliente',customer?.customer_label||order.customer_id.slice(0,8)],['Sesión',order.session_id.slice(0,8)],['Clic de compra',order.checkout_event_id.slice(0,8)]]:[]),
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
  if(!order||trackFetching)return;
  trackFetching=true;
  request(`/api/track?run_id=${encodeURIComponent(data.run_id)}&courier_id=${encodeURIComponent(selected)}`).then(history=>{
    if(selected!==selectedAtRequest||lastData?.run_id!==runAtRequest||lastData.couriers.find(c=>c.courier_id===selected)?.order_id!==row.order_id)return;
    const points=history.rows.filter(p=>p.order_id===row.order_id).map(p=>project(p.latitude,p.longitude).join(','));
    $('route').setAttribute('points',points.join(' '));
    $('rate-note').textContent='El gráfico se consulta desde el histórico GPS en ClickHouse.';
  }).catch(()=>{$('rate-note').textContent='No se pudo consultar el recorrido. Se reintentará en la siguiente actualización.';}).finally(()=>{trackFetching=false;});
}
function renderCustomers(data){
  const metrics=data.customer_metrics||{};
  for(const [id,key] of [['customer-sessions','sessions'],['customer-clicks','clicks'],['customer-checkouts','checkouts'],['customer-abandons','abandoned_sessions']])$(id).textContent=fmt.format(Number(metrics[key]||0));
  const sim=lastSimulation;
  const hasAI=['ollama','hybrid'].includes(sim.agent_mode);
  const modeText=sim.agent_mode==='hybrid'?`${sim.ai_customers} clientes con IA · ${sim.traffic_customers} con simulador de tráfico`:sim.agent_mode==='traffic'?`${sim.traffic_customers} clientes con simulador de tráfico · sin IA`:sim.agent_mode==='ollama'?'IA local · '+sim.model:'Política local · sin modelo de IA';
  $('agent-label').textContent=sim.mode==='customers'?`${modeText}${sim.agent_state==='limit_reached'?' · IA: límite de llamadas alcanzado':sim.agent_state==='error'?' · IA: decisiones detenidas por error':!sim.running?' · ejecución parada':''}${hasAI?` · ${sim.model_calls||0}/${sim.max_model_calls||120} llamadas`:''}`:'Flota anterior o sin ejecución de clientes';
  const all=data.customers||[];
  const isAI=c=>sim.agent_mode==='ollama'||sim.agent_mode==='hybrid'&&Number(c.customer_label.replace(/\D/g,''))<=Number(sim.ai_customers);
  const ai=all.filter(isAI);
  const rest=all.filter(c=>!isAI(c)).sort((a,b)=>b.event_time.localeCompare(a.event_time)||a.customer_id.localeCompare(b.customer_id));
  const visible=showAllCustomers?all:[...ai.slice(0,12),...rest.slice(0,Math.max(0,12-ai.slice(0,12).length))];
  $('customer-list-note').textContent=`${visible.length} de ${all.length} clientes · resumen: IA y actividad reciente. Los contadores incluyen a todos.`;
  $('toggle-customers').hidden=all.length<=12;$('toggle-customers').textContent=showAllCustomers?'Mostrar resumen':'Mostrar todos los clientes';$('toggle-customers').setAttribute('aria-expanded',String(showAllCustomers));
  $('customers-body').innerHTML=visible.map(c=>{
    const order=(data.orders||[]).find(o=>o.order_id===c.order_id);
    const courier=(data.couriers||[]).find(p=>p.order_id===c.order_id);
    const context=c.product_name||c.restaurant_name||c.objective;
    const following=c.order_id?`<span>${escapeHTML(c.order_id.slice(0,8))} · ${escapeHTML(states[order?.status]||(c.stage==='delivered'?'Entregado':'Pendiente de publicación'))}</span>${courier&&order?.status!=='delivered'?`<button class="secondary follow-order" data-order="${escapeHTML(c.order_id)}" aria-label="Ver reparto de ${escapeHTML(c.customer_label)}">Ver reparto</button>`:''}`:'Todavía sin compra';
    return `<tr><td><strong>${escapeHTML(c.customer_label)}</strong><small>Presupuesto ${money(c.budget_minor)}</small><small>${escapeHTML(isAI(c)?'IA local':sim.agent_mode==='policy'?'Política de prueba':'Simulador de tráfico')}</small></td><td><strong>${escapeHTML(customerActions[c.action]||c.action)}</strong><small>${escapeHTML(context)}</small><p>${escapeHTML(c.reason)}</p></td><td>${money(c.cart_total_minor)}</td><td>${following}</td></tr>`;
  }).join('')||'<tr><td colspan="4">Inicia el modo clientes. Las decisiones aparecerán tras publicarse en ClickHouse.</td></tr>';
  $('customer-activity').innerHTML=(data.activity||[]).map(a=>`<li><time>${clock(a.event_time)}</time><strong>${escapeHTML(a.customer_label)} · ${escapeHTML(customerActions[a.action]||a.action)}</strong><span>${escapeHTML(a.reason)} <small>${a.decision_mode==='ollama'?'Decisión del modelo':decisionLabel(a.decision_mode)}</small></span></li>`).join('')||'<li>Aún no hay acciones publicadas en esta ejecución.</li>';
}
function renderOperations(data){
  lastData=data;const m=data.metrics||{};
  for(const key of ['active','delivered','cancelled','late'])$(key).textContent=fmt.format(Number(m[key]||0));
  $('amount').textContent=money(m.delivered_amount_minor);
  $('order-count').textContent=`${fmt.format(Number(m.orders||0))} pedidos${data.truncated?' · lista limitada a 200':''}`;
  const labels=Object.fromEntries((data.customers||[]).map(c=>[c.customer_id,c.customer_label]));
  $('orders-body').innerHTML=(data.orders||[]).map(row=>`<tr><td>${escapeHTML(row.order_id.slice(0,8))}</td><td>${row.customer_id?`${escapeHTML(labels[row.customer_id]||row.customer_id.slice(0,8))}<small>Sesión ${escapeHTML(row.session_id.slice(0,8))}</small>`:lastSimulation.mode==='customers'?'Enlace pendiente':'Demo anterior'}</td><td>${escapeHTML(row.restaurant_id.replace('fictional-madrid-','Madrid · local '))}</td><td><span class="badge ${escapeHTML(row.status)}">${escapeHTML(states[row.status]||row.status)}</span></td><td>${money(row.amount_minor)}</td><td>${clock(row.order_created_at)}</td><td>${clock(row.promised_delivery_at)}</td></tr>`).join('')||'<tr><td colspan="7">Sin compras en esta ejecución. Esperando un checkout confirmado.</td></tr>';
  const rate=data.positions_by_5s||[];const max=Math.max(1,...rate.map(r=>Number(r.positions)));
  $('rate').replaceChildren(...rate.map(row=>{const bar=document.createElement('div');bar.style.height=`${Number(row.positions)/max*100}%`;bar.title=`${clock(row.bucket)} · ${row.positions} posiciones`;return bar;}));
  renderMap(data);
  renderCustomers(data);
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
    showError(queue.publisher_error?`La publicación está reintentando: ${queue.publisher_error}. Los eventos aceptados siguen en cola.`:lastSimulation.error||(lastSimulation.traffic_state==='error'?'El simulador de tráfico se ha detenido por un error. Revisa la cola y reinicia la ejecución.':'')||(lastSimulation.agent_state==='error'?'Se han detenido las decisiones después de tres errores. Revisa Ollama y reinicia la ejecución; las entregas ya creadas siguen avanzando.':''));
  }catch(error){showError(`No se pudo actualizar: ${error.message}. Se conservan los datos anteriores y se reintentará.`);$('freshness').textContent='Consulta fallida · posiciones anteriores';}
  finally{fetching=false;clearTimeout(refreshTimer);refreshTimer=setTimeout(poll,2000);}
}
async function control(action){
  controlling=true;buttons();
  try{lastSimulation=await request(`/api/simulation/${action}`,action==='start'?{fleet:Number($('fleet').value),interval:2,seed:42,mode:$('agent-mode').value==='legacy'?'legacy':'customers',agent_mode:$('agent-mode').value==='legacy'?'ollama':$('agent-mode').value,customers:Number($('customer-count').value)}:{});showError('');}
  catch(error){showError(error.message);}
  finally{controlling=false;buttons();await poll();}
}
if(!readOnly){$('start').addEventListener('click',()=>control('start'));$('stop').addEventListener('click',()=>control('stop'));}
$('courier').addEventListener('change',()=>selectCourier($('courier').value));
$('toggle-customers').addEventListener('click',()=>{showAllCustomers=!showAllCustomers;if(lastData)renderCustomers(lastData);});
$('customers-body').addEventListener('click',event=>{
  const button=event.target.closest('[data-order]');if(!button)return;
  const courier=lastData?.couriers.find(c=>c.order_id===button.dataset.order);if(!courier)return;
  selectCourier(courier.courier_id);$('tracking').scrollIntoView({behavior:'auto',block:'start'});
});
$('origin').addEventListener('change',()=>loadNavigation(true));
$('manual').addEventListener('click',async()=>{
  $('manual').disabled=true;
  manualEvent=manualEvent||{schema_version:1,event_id:crypto.randomUUID(),session_id:session,event_time:new Date().toISOString(),event_type:'search',section:'search',city_id:'madrid',source:'atlas-dashboard',source_kind:'demo_live'};
  try{const data=await request('/api/events',{events:[manualEvent]});$('manual-status').textContent=data.accepted?'Búsqueda recibida en cola; pendiente de publicación.':'Búsqueda ya recibida; reintento reconocido.';manualEvent=null;$('manual').textContent='Registrar una búsqueda manual';}
  catch(error){$('manual-status').textContent=`No se confirmó el envío: ${error.message}`;$('manual').textContent='Reintentar la misma búsqueda';}
  finally{$('manual').disabled=false;}
});
const uses={otto_archive:'Eventos públicos OTTO',rees46_events:'Eventos públicos REES46',eleme_samples:'Muestras públicas Ele.me',glovo_products:'Catálogo publicado; sin clics',orders:'Pedidos históricos TRD / Meituan',clicks:'Secuencias históricas TRD / Meituan',restaurants:'Restaurantes históricos TRD',foods:'Productos históricos TRD',order_items:'Líneas de pedidos históricos',otto_scale_benchmark:'Filas derivadas para estrés',otto_replay:'Reproducción histórica',app_events:'Navegación propia, origen etiquetado',courier_positions:'GPS sintético',order_events:'Estados de pedidos sintéticos',customer_activity:'Decisiones de clientes sintéticos',customer_orders:'Compras enlazadas al checkout',customer_latest_state:'Último estado agregado de clientes'};
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
