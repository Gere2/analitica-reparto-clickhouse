'use strict';
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat('en-GB');
const money=value=>new Intl.NumberFormat('en-IE',{style:'currency',currency:'EUR'}).format(Number(value||0)/100);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock=value=>value?new Date(value.replace(' ','T')+'Z').toLocaleTimeString('en-GB'): '—';
const states={created:'Created',preparing:'Preparing',picked_up:'Picked up',en_route:'On the way',delivered:'Delivered',cancelled:'Cancelled'};
let selected='',lastData=null,lastSimulation={},refreshTimer=null,fetching=false,controlling=false,manualEvent=null;
let navigationFetching=false,navigationAt=0,navigationOrigin='';
let trackFetching=false,showAllCustomers=false;
const decisionLabel=mode=>({ollama:'Local AI',traffic:'Traffic simulator',policy:'Test policy',system:'System'}[mode]||mode);
const customerActions={session_started:'Starts a session',search:'Searches for food',open_restaurant:'Compares a restaurant',open_product:'Opens a product',add_to_cart:'Adds to cart',remove_from_cart:'Removes from cart',checkout:'Confirms the purchase',abandon:'Abandons the session',delivery_completed:'Receives the order'};
const session=crypto.randomUUID();
const readOnly=Boolean(document.querySelector('meta[name="atlas-readonly"]'));
const views={
  simulated:'Fictional customers moved by the traffic simulator: rules and random choices with a fixed seed. Orders placed by hand in the mini-app also appear here. Every customer type shares the same courier fleet.',
  ai:'Fictional customers whose next step is chosen by a local language model (Ollama) on the demo server. Python validates every decision before it becomes a click or a purchase. Every customer type shares the same courier fleet.',
  real:'Real public datasets downloaded from their publishers. They have no GPS or orders and are never mixed with the simulation.'};
let view=new URLSearchParams(location.search).get('view'),liveView='simulated',datasetsAt=0,datasetsFetching=false;
if(!views[view])view='simulated';
const orderKind=row=>row.decision_mode==='ollama'?'ai':'simulated';
function metricsForView(data,key){
  if(data[key+'_by_kind'])return data[key+'_by_kind'][view]||null;
  // During a staged rollout the old server only returns totals. Those are safe
  // for the simulated view only when this exact run cannot contain AI orders.
  if(data.run_id!==lastSimulation.run_id)return null;
  const allSimulated=lastSimulation.mode==='legacy'||['traffic','policy'].includes(lastSimulation.agent_mode);
  return allSimulated?(view==='simulated'?data[key]||null:{}):null;
}
async function request(path,body){
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch(path,{signal:controller.signal,cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
    const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);return data;
  }finally{clearTimeout(timeout);}
}
function showError(message){$('error').hidden=!message;$('error').textContent=message;}
function buttons(){ if(readOnly)return; if(lastSimulation.running){$('fleet').value=String(lastSimulation.fleet);$('customer-count').value=String(lastSimulation.customers||3);$('agent-mode').value=lastSimulation.mode==='customers'?lastSimulation.agent_mode:'legacy';} $('start').disabled=controlling||lastSimulation.running;$('stop').disabled=controlling||!lastSimulation.running;for(const id of ['fleet','agent-mode','customer-count'])$(id).disabled=controlling||lastSimulation.running; }
function selectCourier(id){selected=id;$('courier').value=id;if(lastData)renderMap(lastData);}
function renderMap(data){
  const couriers=data.couriers||[];
  if(!couriers.some(row=>row.courier_id===selected))selected=couriers[0]?.courier_id||'';
  if($('courier').options.length!==couriers.length||couriers.some((r,i)=>$('courier').options[i]?.value!==r.courier_id)){
    $('courier').replaceChildren(...couriers.map((row,i)=>{const option=document.createElement('option');option.value=row.courier_id;option.textContent=`Courier ${String(i+1).padStart(2,'0')} · ${row.courier_id.slice(0,8)}`;return option;}));
  }
  $('courier').value=selected;
  const row=couriers.find(r=>r.courier_id===selected);
  if(!row){fleetMap.update(data,selected,null);$('freshness').textContent='No positions';$('courier-detail').innerHTML='<dt>Status</dt><dd>Waiting for positions</dd>';return;}
  const order=(data.orders||[]).find(o=>o.order_id===row.order_id);
  const customer=(data.customers||[]).find(c=>c.customer_id===order?.customer_id);
  const age=Math.max(0,(Date.now()-Date.parse(row.event_time.replace(' ','T')+'Z'))/1000);
  $('freshness').textContent=`${couriers.length} couriers · selected position: ${age.toFixed(1)} s ago`;
  $('courier-detail').innerHTML=[['Order',row.order_id.startsWith('00000000-')?'No order assigned':row.order_id.slice(0,8)],['Status',states[order?.status]||'Available'],
    ...(order?.customer_id?[['Customer',customer?.customer_label||order.customer_id.slice(0,8)],['Session',order.session_id.slice(0,8)],['Purchase click',order.checkout_event_id.slice(0,8)]]:[]),
    ['Latitude',Number(row.latitude).toFixed(6)],['Longitude',Number(row.longitude).toFixed(6)],
    ['Simulated speed',`${Number(row.speed_kmh).toFixed(1)} km/h`],['Simulated accuracy',`${row.accuracy_m} m`],
    ['Event time',clock(row.event_time)],['Age',`${age.toFixed(1)} s`],
    ['Until received by API',`${Math.max(0,Number(row.receipt_delay_ms))} ms`]]
    .map(([key,value])=>`<dt>${escapeHTML(key)}</dt><dd>${escapeHTML(value)}</dd>`).join('');
  fleetMap.update(data,selected,order);
  const selectedAtRequest=selected,runAtRequest=data.run_id;
  if(!order||trackFetching)return;
  trackFetching=true;
  request(`/api/track?run_id=${encodeURIComponent(data.run_id)}&courier_id=${encodeURIComponent(selected)}`).then(history=>{
    if(selected!==selectedAtRequest||lastData?.run_id!==runAtRequest||lastData.couriers.find(c=>c.courier_id===selected)?.order_id!==row.order_id)return;
    fleetMap.setHistory(history.rows.filter(p=>p.order_id===row.order_id),[runAtRequest,selectedAtRequest,row.order_id].join(':'));
    $('rate-note').textContent='The chart is queried from the GPS history in ClickHouse.';
  }).catch(()=>{$('rate-note').textContent='The path could not be queried. It will be retried on the next refresh.';}).finally(()=>{trackFetching=false;});
}
function renderCustomers(data){
  const metrics=metricsForView(data,'customer_metrics');
  for(const [id,key] of [['customer-sessions','sessions'],['customer-clicks','clicks'],['customer-checkouts','checkouts'],['customer-abandons','abandoned_sessions']])$(id).textContent=metrics?fmt.format(Number(metrics[key]||0)):'—';
  const sim=lastSimulation;
  const hasAI=['ollama','hybrid'].includes(sim.agent_mode);
  const modeText=sim.agent_mode==='hybrid'?`${sim.ai_customers} AI customers · ${sim.traffic_customers} with the traffic simulator`:sim.agent_mode==='traffic'?`${sim.traffic_customers} customers with the traffic simulator · no AI`:sim.agent_mode==='ollama'?'Local AI · '+sim.model:'Local policy · no AI model';
  $('agent-label').textContent=sim.mode==='customers'?`${modeText}${sim.agent_state==='limit_reached'?' · AI: call limit reached':sim.agent_state==='error'?' · AI: decisions stopped by an error':!sim.running?' · run stopped':''}${hasAI?` · ${sim.model_calls||0}/${sim.max_model_calls||120} calls`:''}`:'Previous fleet or no customer run';
  const isAI=c=>c.decision_mode==='ollama'||sim.agent_mode==='ollama'||sim.agent_mode==='hybrid'&&Number(c.customer_label.replace(/\D/g,''))<=Number(sim.ai_customers);
  const aiIds=new Set((data.customers||[]).filter(isAI).map(c=>c.customer_id));
  const all=(data.customers||[]).filter(c=>isAI(c)===(view==='ai'));
  const ai=all.filter(isAI);
  const rest=all.filter(c=>!isAI(c)).sort((a,b)=>b.event_time.localeCompare(a.event_time)||a.customer_id.localeCompare(b.customer_id));
  const visible=showAllCustomers?all:[...ai.slice(0,12),...rest.slice(0,Math.max(0,12-ai.slice(0,12).length))];
  $('customer-list-note').textContent=`${visible.length} of ${all.length} ${view==='ai'?'AI agents':'simulated customers'} · most recent activity first. The counters cover this customer type only.`;
  $('toggle-customers').hidden=all.length<=12;$('toggle-customers').textContent=showAllCustomers?'Show summary':'Show all customers';$('toggle-customers').setAttribute('aria-expanded',String(showAllCustomers));
  $('customers-body').innerHTML=visible.map(c=>{
    const order=(data.orders||[]).find(o=>o.order_id===c.order_id);
    const courier=(data.couriers||[]).find(p=>p.order_id===c.order_id);
    const context=c.product_name||c.restaurant_name||c.objective;
    const following=c.order_id?`<span>${escapeHTML(c.order_id.slice(0,8))} · ${escapeHTML(states[order?.status]||(c.stage==='delivered'?'Delivered':'Waiting to be published'))}</span>${courier&&order?.status!=='delivered'?`<button class="secondary follow-order" data-order="${escapeHTML(c.order_id)}" aria-label="View delivery for ${escapeHTML(c.customer_label)}">View delivery</button>`:''}`:'No purchase yet';
    return `<tr><td><strong>${escapeHTML(c.customer_label)}</strong><small>Budget ${money(c.budget_minor)}</small><small>${escapeHTML(isAI(c)?'Local AI':sim.agent_mode==='policy'?'Test policy':'Traffic simulator')}</small></td><td><strong>${escapeHTML(customerActions[c.action]||c.action)}</strong><small>${escapeHTML(context)}</small><p>${escapeHTML(c.reason)}</p></td><td>${money(c.cart_total_minor)}</td><td>${following}</td></tr>`;
  }).join('')||`<tr><td colspan="4">${view==='ai'?(readOnly?'This run has no AI agents. The demo server chooses which kind of run is active.':'This run has no AI agents. Stop it and start a run with “AI + mass traffic” (three AI agents plus simulated traffic) or “Local AI · Ollama”.'):'Start customer mode. Decisions will appear once they are published to ClickHouse.'}</td></tr>`;
  $('customer-activity').innerHTML=(data.activity||[]).filter(a=>(a.decision_mode==='ollama'||aiIds.has(a.customer_id))===(view==='ai')).slice(0,30).map(a=>`<li><time>${clock(a.event_time)}</time><strong>${escapeHTML(a.customer_label)} · ${escapeHTML(customerActions[a.action]||a.action)}</strong><span>${escapeHTML(a.reason)} <small>${a.decision_mode==='ollama'?'Model decision':decisionLabel(a.decision_mode)}</small></span></li>`).join('')||'<li>No actions published in this run yet.</li>';
}
function renderOperations(data){
  lastData=data;const m=metricsForView(data,'metrics');
  for(const key of ['active','delivered','cancelled','late'])$(key).textContent=m?fmt.format(Number(m[key]||0)):'—';
  $('amount').textContent=m?money(m.delivered_amount_minor):'—';
  $('metrics-note').hidden=Boolean(m&&metricsForView(data,'customer_metrics'));
  $('order-count').textContent=m?`${fmt.format(Number(m.orders||0))} ${Number(m.orders)===1?'order':'orders'}${view==='ai'?' by AI agents':''}${data.truncated?' · list limited to the latest 200 orders of the run':''}`:'Per-type counts need a demo server update';
  const labels=Object.fromEntries((data.customers||[]).map(c=>[c.customer_id,c.customer_label]));
  $('orders-body').innerHTML=(data.orders||[]).filter(row=>orderKind(row)===view).map(row=>`<tr><td>${escapeHTML(row.order_id.slice(0,8))}</td><td>${row.customer_id?`${escapeHTML(labels[row.customer_id]||(row.decision_mode==='manual'?'Mini-app (manual)':row.customer_id.slice(0,8)))}<small>Session ${escapeHTML(row.session_id.slice(0,8))}</small>`:lastSimulation.mode==='customers'?'Link pending':'Previous demo'}</td><td>${escapeHTML(row.restaurant_id.replace('fictional-madrid-','Madrid · venue '))}</td><td><span class="badge ${escapeHTML(row.status)}">${escapeHTML(states[row.status]||row.status)}</span></td><td>${money(row.amount_minor)}</td><td>${clock(row.order_created_at)}</td><td>${clock(row.promised_delivery_at)}</td></tr>`).join('')||`<tr><td colspan="7">${view==='ai'?'No purchases by AI agents in this run.':'No purchases in this run. Waiting for a confirmed checkout.'}</td></tr>`;
  const rate=data.positions_by_5s||[];const max=Math.max(1,...rate.map(r=>Number(r.positions)));
  $('rate').replaceChildren(...rate.map(row=>{const bar=document.createElement('div');bar.style.height=`${Number(row.positions)/max*100}%`;bar.title=`${clock(row.bucket)} · ${row.positions} positions`;return bar;}));
  renderMap(data);
  renderCustomers(data);
}
function renderNavigation(data){
  const totals={};(data.rows||[]).forEach(row=>totals[row.event_type]=(totals[row.event_type]||0)+Number(row.events));
  const steps=[['search','Searches'],['restaurant_opened','Restaurants'],['product_opened','Products'],['cart_added','Carts'],['order_submitted','Orders submitted']];
  const max=Math.max(1,...Object.values(totals));
  $('actions').innerHTML=steps.map(([key,label])=>`<div><span>${label}</span><strong>${fmt.format(totals[key]||0)}</strong><div class="action-track"><i style="width:${(totals[key]||0)/max*100}%"></i></div></div>`).join('');
  $('navigation-count').textContent=`${fmt.format(data.events)} Madrid events · ${$('origin').selectedOptions[0].textContent.toLowerCase()} · whole Atlas history${data.truncated?' · only the first groups shown':''} · queried ${new Date().toLocaleTimeString('en-GB')} (10 s interval).`;
}
async function loadNavigation(force=false){
  const origin=$('origin').value;
  if(navigationFetching||(!force&&navigationOrigin===origin&&Date.now()-navigationAt<10000))return;
  navigationFetching=true;
  try{const data=await request(`/api/summary?city_id=madrid&source_kind=${origin}`);if(origin===$('origin').value){renderNavigation(data);navigationAt=Date.now();navigationOrigin=origin;}}
  catch(error){$('navigation-count').textContent=`Browsing query failed: ${error.message}. It will be retried.`;}
  finally{navigationFetching=false;}
}
async function poll(){
  if(fetching||document.hidden)return;fetching=true;
  try{
    lastSimulation=await request('/api/simulation');buttons();
    const [data,queue]=await Promise.all([request('/api/operations'),request('/api/status')]);
    renderOperations(data);$('pending').textContent=fmt.format(queue.pending);loadNavigation();
    const state=lastSimulation.error?`Simulation stopped: ${lastSimulation.error}`:lastSimulation.running?`Simulation running · ${lastSimulation.fleet} couriers · requested interval: ${lastSimulation.interval_seconds} s`:'Simulation stopped; the history is kept';
    $('status').textContent=`${state}. Last query: ${new Date().toLocaleTimeString('en-GB')}${lastSimulation.run_id?` · run ${lastSimulation.run_id.slice(0,8)}`:''}.`;
    showError(queue.publisher_error?`Publishing is retrying: ${queue.publisher_error}. Accepted events stay in the queue.`:lastSimulation.error||(lastSimulation.traffic_state==='error'?'The traffic simulator stopped because of an error. Check the queue and restart the run.':'')||(lastSimulation.agent_state==='error'?'Decisions stopped after three errors. Check Ollama and restart the run; deliveries already created keep progressing.':''));
  }catch(error){showError(`Could not refresh: ${error.message}. The previous data is kept and it will be retried.`);$('freshness').textContent='Query failed · previous positions';}
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
  try{const data=await request('/api/events',{events:[manualEvent]});$('manual-status').textContent=data.accepted?'Search received in the queue; waiting to be published.':'Search already received; retry recognized.';manualEvent=null;$('manual').textContent='Record a manual search';}
  catch(error){$('manual-status').textContent=`The send was not confirmed: ${error.message}`;$('manual').textContent='Retry the same search';}
  finally{$('manual').disabled=false;}
});
const uses={otto_archive:'Public OTTO events',rees46_events:'Public REES46 events',eleme_samples:'Public Ele.me samples',glovo_products:'Published catalog; no clicks',criteo_uplift:'Real advertising experiment (Criteo)',orders:'Historical TRD / Meituan orders',clicks:'Historical TRD / Meituan sequences',restaurants:'Historical TRD restaurants',foods:'Historical TRD products',order_items:'Historical order lines',otto_scale_benchmark:'Derived rows for stress testing',otto_replay:'Historical replay',app_events:'Our own browsing, labelled origin',courier_positions:'Synthetic GPS',order_events:'Synthetic order statuses',customer_activity:'Synthetic customer decisions',customer_orders:'Purchases linked to checkout',customer_latest_state:'Latest aggregate customer state'};
async function loadContext(){
  const results=await Promise.allSettled([request('/api/inventory'),request('/api/catalog')]);
  if(results[0].status==='fulfilled')$('inventory-body').innerHTML=results[0].value.rows.filter(r=>uses[r.name]&&Number(r.total_rows)>0).map(row=>`<tr><td>${escapeHTML(row.database+'.'+row.name)}</td><td>${fmt.format(Number(row.total_rows||0))}</td><td>${escapeHTML(row.disk)}</td><td>${escapeHTML(uses[row.name])}</td></tr>`).join('');
  else $('inventory-body').innerHTML='<tr><td colspan="4">The inventory could not be queried. Reload to retry.</td></tr>';
  if(results[1].status==='fulfilled'){
    const catalog=results[1].value;$('catalog-note').textContent=catalog.meaning+' The simulated positions do not belong to these businesses.';
    $('catalog').innerHTML=catalog.rows.slice(0,12).map(row=>`<article><strong>${escapeHTML(row.product_name)}</strong><p>${escapeHTML(row.store_name)} · ${escapeHTML(row.collection_section)}</p></article>`).join('')||'<p class="empty">The simulation works without this catalog. It appears once the Glovo dataset is loaded on the demo server.</p>';
  }else $('catalog').innerHTML='<p class="empty">The catalog is not available. Reload to retry; the fleet keeps working.</p>';
}
const percent=(value,digits=2)=>value!=null&&Number.isFinite(Number(value))?`${(Number(value)*100).toFixed(digits)}%`:'—';
const timing=result=>`${fmt.format(result.rows_read)} rows read in ${result.elapsed_ms} ms`;
function notLoaded(script){return `<p class="empty">Not loaded on ${readOnly?'the demo server':`this computer. Run <code>python scripts/${script} download</code> and then <code>load</code>`}.</p>`;}
function renderDatasets(data){
  const criteo=data.criteo,glovo=data.glovo;
  if(criteo){
    const [control,treated]=[0,1].map(t=>criteo.rows.find(r=>Number(r.treatment)===t)||{});
    const effect=(key,digits)=>{
      if(treated[key]==null||control[key]==null)return '<dd>—</dd><small>Both groups are needed</small>';
      const base=Number(control[key]),diff=Number(treated[key])-base,sign=diff>=0?'+':'';
      return `<dd>${sign}${(diff*100).toFixed(digits)} pp</dd><small>${base>0?`${sign}${(diff/base*100).toFixed(0)}% compared with control`:'Relative difference unavailable: control rate is zero'}</small>`;
    };
    $('criteo-body').innerHTML=`<div class="table-wrap"><table><thead><tr><th>Group</th><th>Users</th><th>Saw the ad</th><th>Visited</th><th>Bought</th></tr></thead><tbody>${[['Treatment · campaign',treated],['Control · no campaign',control]].map(([label,row])=>`<tr><td>${label}</td><td>${fmt.format(Number(row.users||0))}</td><td>${percent(row.exposure_rate)}</td><td>${percent(row.visit_rate)}</td><td>${percent(row.conversion_rate,3)}</td></tr>`).join('')}</tbody></table></div><dl class="effects"><div><dt>Observed difference in visits</dt>${effect('visit_rate',2)}</div><div><dt>Observed difference in purchases</dt>${effect('conversion_rate',3)}</div></dl>`;
    $('criteo-time').textContent=timing(criteo);
  }else{$('criteo-body').innerHTML=notLoaded('criteo.py');$('criteo-time').textContent='';}
  if(glovo){
    const total=key=>glovo.rows.reduce((sum,row)=>sum+Number(row[key]),0);
    $('glovo-body').innerHTML=`<dl class="effects"><div><dt>Products</dt><dd>${fmt.format(total('products'))}</dd></div><div><dt>Countries</dt><dd>${glovo.rows.length}</dd></div><div><dt>In Madrid</dt><dd>${fmt.format(total('madrid_products'))}</dd></div></dl><div class="table-wrap"><table><thead><tr><th>Country</th><th>Products</th><th>Stores</th></tr></thead><tbody>${glovo.rows.slice(0,8).map(row=>`<tr><td>${escapeHTML(row.country_code)}</td><td>${fmt.format(Number(row.products))}</td><td>${fmt.format(Number(row.stores))}</td></tr>`).join('')}</tbody></table></div>`;
    $('glovo-time').textContent=timing(glovo);
  }else{$('glovo-body').innerHTML=notLoaded('glovo.py');$('glovo-time').textContent='';}
  $('datasets-time').textContent=`Queried at ${clock(data.queried_at)}${readOnly?'; shared results are refreshed at most once a minute':''}.`;
}
async function loadDatasets(force=false){
  if(datasetsFetching||(!force&&Date.now()-datasetsAt<60000))return;
  datasetsFetching=true;$('rerun-datasets').disabled=true;
  try{renderDatasets(await request('/api/datasets'));datasetsAt=Date.now();}
  catch(error){
    for(const id of ['criteo-body','glovo-body'])$(id).innerHTML=`<p class="empty">The dataset query is unavailable: ${escapeHTML(error.message)}. The demo server may need updating; live tracking remains available. Run it again to retry.</p>`;
    for(const id of ['criteo-time','glovo-time','datasets-time'])$(id).textContent='';
  }
  finally{datasetsFetching=false;$('rerun-datasets').disabled=false;}
}
function setView(next){
  view=views[next]?next:'simulated';
  if(view!=='real')liveView=view;
  document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));
  $('live-view').hidden=view==='real';$('real-view').hidden=view!=='real';
  $('view-note').textContent=views[view];
  const url=new URL(location.href);url.searchParams.set('view',view);history.replaceState(null,'',url);
  // Suggest the matching run type; a running simulation keeps its own settings.
  if(!readOnly&&!lastSimulation.running&&view!=='real')$('agent-mode').value=view==='ai'?'hybrid':'traffic';
  if(view==='real')loadDatasets();else if(lastData)renderOperations(lastData);
}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
$('rerun-datasets').addEventListener('click',()=>loadDatasets(true));
document.querySelector('nav').addEventListener('click',event=>{
  const href=event.target.closest('a[href^="#"]')?.getAttribute('href');
  const target=href&&document.querySelector(href);
  if(target&&Boolean(target.closest('#real-view'))!==(view==='real'))setView(view==='real'?liveView:'real');
});
const fleetMap=new AtlasFleetMap($('map'),selectCourier);
window.addEventListener('pagehide',event=>{if(!event.persisted)fleetMap.destroy();});
setView(view);poll();loadContext();
document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
