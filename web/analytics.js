'use strict';
const $=id=>document.getElementById(id);
const fmt=new Intl.NumberFormat('en-GB',{maximumFractionDigits:2});
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=v=>Number.isFinite(Number(v))?fmt.format(Number(v)):'Unavailable';
const bytes=v=>{const n=Number(v);return n>=1073741824?number(n/1073741824)+' GiB':n>=1048576?number(n/1048576)+' MiB':n>=1024?number(n/1024)+' KiB':number(n)+' B';};
const names={journey:['Customer Journey','Which steps do customer sessions reach, in event-time order?'],performance:['ClickHouse Performance','How do storage layout and query design affect the work ClickHouse does?'],otto:['OTTO Events','How does a large ecommerce event history change over time?'],rees46:['Marketplace Trends','How do actions, categories and brands vary across the loaded months?'],glovo:['Catalog Explorer','How is the published product catalog distributed across locations and stores?'],eleme:['Recommendation Samples','How do the loaded recommendation samples vary by day, hour and meal period?'],criteo:['Advertising Groups','What outcomes appear in the released treatment and control samples?']};
let panel=new URLSearchParams(location.search).get('panel');if(!names[panel])panel='journey';
let generation=0,controller=null,comparisonGeneration=0,lastData=null;
const human=v=>String(v).replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
function table(headers,rows){return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function stats(values){return `<dl class="analytics-stats">${values.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`;}
function note(value){return `<p class="analysis-note">${esc(value)}</p>`;}
function availability(message){return `<div class="availability"><h2>No data for this selection yet</h2><p>${esc(message)}</p><a href="/#tracking">Check the host and live operations</a></div>`;}
function bars(rows,{percent=false,base=null}={}){
  if(!rows.length)return '<p class="empty">No observations for this selection.</p>';
  const max=base??Math.max(...rows.map(r=>Number(r.value)||0),1);
  return `<div class="bar-chart">${rows.map(r=>{const n=Number(r.value)||0;const width=Math.max(0,Math.min(100,max>0?n/max*100:0));return `<div class="bar-row"><span class="bar-label">${esc(r.label)}</span><div class="bar-track" aria-hidden="true"><div class="bar-fill" style="--value:${width}%"></div></div><span class="bar-value">${esc(number(n))}${percent?'%':''}${r.share==null?'':` <small>(${esc(number(r.share))}%)</small>`}</span></div>`;}).join('')}</div>`;
}
function timeline(rows){
  if(!rows.length)return '<p class="empty">No observations for this selection.</p>';
  const series=[...new Set(rows.map(r=>r.series||'Events'))],labels=[...new Set(rows.map(r=>r.label))];
  const max=Math.max(...rows.map(r=>Number(r.value)||0),1);
  return `<div class="chart-legend">${series.map((s,i)=>`<span><i data-series="${i}" aria-hidden="true"></i>${esc(s)}</span>`).join('')}</div><div class="chart-scroll"><div class="time-chart" role="img" aria-label="Event counts by time. Exact values are available in the data table below.">${labels.map(label=>`<div class="time-bucket">${series.map((s,i)=>{const row=rows.find(r=>r.label===label&&(r.series||'Events')===s),value=Number(row?.value)||0;return `<div class="time-column" data-series="${i}" style="--value:${value/max*100}%" title="${esc(label+' · '+s+': '+number(value))}"></div>`;}).join('')}</div>`).join('')}</div></div><div class="time-axis"><span>${esc(labels[0])}</span><span>${esc(labels.at(-1))}</span></div>`;
}
function figure(title,caption,rows,{time=false,percent=false,base=null,full=false}={}){
  return `<figure class="analysis-figure${full?' full':''}"><h2>${esc(title)}</h2><figcaption>${esc(caption)}</figcaption>${time?timeline(rows):bars(rows,{percent,base})}<details class="chart-data"><summary>View chart data</summary>${table(['Group',...(time?['Series']:[]),'Value'],rows.map(r=>[esc(r.label),...(time?[esc(r.series||'Events')]:[]),esc(number(r.value))]))}</details></figure>`;
}
function queries(data){$('query-list').innerHTML=(data.queries||[]).map(q=>`<details class="query-detail"><summary>${esc(q.label)}<span>${esc(number(q.elapsed_ms))} ms · ${esc(number(q.rows_read))} rows read · ${esc(bytes(q.bytes_read))}</span></summary><pre><code>${esc(q.sql)}</code></pre></details>`).join('')||'<p class="empty">A query appears after this view has data.</p>';}
function journey(data){
  if(!data.available)return availability(data.message);
  const cohort=Number(data.cohort_sessions)||0,checkout=Number(data.steps?.at(-1)?.sessions)||0;
  const timelineRows=(data.timeline||[]).flatMap(r=>[['Active sessions','active_sessions'],['Checkout sessions','checkout_sessions'],['Abandoned sessions','abandoned_sessions']].map(([series,key])=>({label:r.bucket,series,value:r[key]})));
  return stats([['Started sessions',number(cohort)],['Ordered checkouts',number(checkout)],['Completed funnel',cohort?number(checkout/cohort*100)+'%':'No cohort'],['Observed abandoned sessions',number(data.abandoned_sessions)]])+note(data.definition)+
    `<p class="source-table">delivery_atlas.customer_activity · run ${esc(data.run_id)} · ${esc(data.kind)}</p>`+
    `<div class="analysis-grid">${figure('Ordered session funnel','windowFunnel over millisecond timestamps, after FINAL. Differences include sessions still in progress.',data.steps.map(s=>({label:s.label,value:s.sessions,share:s.share_pct})),{base:cohort})}${figure('Actions stored in ClickHouse','Logical records after ReplacingMergeTree replacement at query time.',data.actions.map(r=>({label:human(r.action),value:r.events})))}${figure('Session activity by minute','Last 60 observed minute buckets. A session can be active in more than one bucket. Gaps are not imputed as zero.',timelineRows,{time:true,full:true})}</div>`+
    note(data.classification+' Sessions without an observed start: '+number(data.excluded_sessions)+'.');
}
function performance(data){
  const tables=data.tables||[],disk=tables.reduce((n,r)=>n+Number(r.disk_bytes||0),0),physical=tables.reduce((n,r)=>n+Number(r.physical_rows||0),0);
  return stats([['ClickHouse version',data.version],['MergeTree tables',number(tables.length)],['Physical rows across listed tables',number(physical)],['Active parts on disk',bytes(disk)]])+note(data.definition)+
    `<div class="analysis-grid">${figure('Storage by table','Bytes on disk from active system.parts. Top 12 tables in delivery and delivery_atlas.',tables.slice().sort((a,b)=>Number(b.disk_bytes)-Number(a.disk_bytes)).slice(0,12).map(r=>({label:r.table,value:r.disk_bytes})))}${figure('Completed query families','Median server time (ms), last hour. Labels include the source table and a shortened query hash.',data.history.map(r=>({label:(r.source_tables.split(',')[0].split('.').at(-1)||'Query')+' / '+r.query_family.slice(0,6),value:r.median_ms})))}</div>`+
    `<section class="section"><h2>Table engines and access patterns</h2><p class="caption">Partitions organise data within a table. Sorting keys and engine behaviour affect how these dashboards read it.</p>${table(['Table / engine','Physical rows','Disk','Compression ratio','Partitions / sorting key'],tables.map(r=>[`<strong>${esc(r.database+'.'+r.table)}</strong><span class="table-secondary">${esc(r.engine)} · ${esc(number(r.active_parts))} parts</span>`,esc(number(r.physical_rows)),esc(bytes(r.disk_bytes)),Number(r.compressed_bytes)>0?esc(number(Number(r.uncompressed_bytes)/Number(r.compressed_bytes)))+'×':'Unavailable',`<code>${esc(r.partition_key||'No partition key')}</code><span class="table-secondary"><code>${esc(r.sorting_key)}</code></span>`]))}</section>`+
    `<section class="section"><h2>Detail versus prepared aggregate</h2><p class="caption">Run two fixed queries and verify their answers match before comparing their cost. Shared results may be reused for 60 seconds.</p><div class="comparison-controls"><label>Workload<select id="workload"><option value="atlas">Atlas · latest synthetic Madrid date</option><option value="otto">OTTO · daily event counts</option></select></label><button id="compare">Compare fixed queries</button></div><div id="comparison" class="comparison-result" role="status">The comparison runs when requested. Large tables can take several seconds.</div></section>`+
    `<section class="section"><h2>Query history</h2>${!data.log_available?note('Query logging is unavailable on this host. Table metadata and the fixed comparison remain separate reads.'):data.history.length?table(['Query family / tables','Completed reads','Median','Slowest','Avg rows read','Peak memory'],data.history.map(r=>[`<code>${esc(r.query_family)}</code><span class="table-secondary">${esc(r.source_tables)}</span>`,esc(number(r.executions)),esc(number(r.median_ms))+' ms',esc(number(r.slowest_ms))+' ms',esc(number(r.average_rows_read)),esc(bytes(r.peak_memory_bytes))])):note('No completed analytical queries have appeared in the last-hour query log yet. This is different from zero query latency.')}</section>`;
}
function historical(data){
  if(!data.available)return availability(data.message)+`<p class="source-table">${esc(data.table)}</p>`;
  return stats(Object.entries(data.metrics||{}).map(([key,v])=>[human(key),number(v)]))+note(data.meaning)+`<p class="source-table">${esc(data.table)}</p><div class="analysis-grid">${data.charts.map((c,i)=>figure(c.title,c.label,c.rows,{time:c.rows.some(r=>r.series),percent:c.title.includes('(%)'),full:i===2})).join('')}</div>`;
}
function comparison(data){
  if(!data.available)return availability(data.message);
  const rows=[{label:'Detail',value:data.detail.elapsed_ms},{label:'Prepared aggregate',value:data.aggregate.elapsed_ms}];
  return `<p>${esc(data.scope)}</p><p class="caption">ClickHouse comparison snapshot: ${esc(data.queried_at||'time unavailable')} UTC</p><p class="${data.same_result?'':'result-warning'}">${data.same_result?'Matching answers verified':'Answers differ. Timing ratio is not a valid optimisation result.'} · ${esc(number(data.result_groups))} groups · ${esc(number(data.logical_events))} logical events</p>`+
    figure('Server execution time','Milliseconds. One read per design, detail first.',rows)+
    table(['Design','Server time','Rows read','Bytes read'],[data.detail,data.aggregate].map(q=>[esc(q.label),esc(number(q.elapsed_ms))+' ms',esc(number(q.rows_read)),esc(bytes(q.bytes_read))]))+
    note(data.definition)+(data.ratio==null?'':note('Observed detail / aggregate time ratio: '+number(data.ratio)+'×. A ratio below 1 means the aggregate took longer.'))+
    [data.detail,data.aggregate].map(q=>`<details class="query-detail"><summary>${esc(q.label)} SQL</summary><pre><code>${esc(q.sql)}</code></pre></details>`).join('');
}
function filters(){
  const params=new URLSearchParams(location.search);let html='';
  const select=(name,label,options,value)=>`<label>${label}<select name="${name}">${options.map(([v,t])=>`<option value="${esc(v)}"${v===value?' selected':''}>${esc(t)}</option>`).join('')}</select></label>`;
  if(panel==='journey')html=select('kind','Customers',[['all','All recorded customers'],['simulated','Simulated customers'],['ai','Customers with model decisions']],params.get('kind')||'all');
  if(panel==='rees46')html=select('period','Historical month',[['ALL','All loaded months'],...['201910','201911','201912','202001','202002','202003','202004'].map(v=>[v,v.slice(0,4)+'-'+v.slice(4)])],params.get('period')||'ALL');
  if(panel==='eleme')html=select('period','Relative sample day',[['ALL','All loaded days'],...Array.from({length:8},(_,i)=>[String(i+1),'Day '+(i+1)])],params.get('period')||'ALL');
  if(panel==='glovo')html=`<label>Country code<input name="country" value="${esc(params.get('country')||'ES')}" pattern="ALL|[A-Z]{2}" maxlength="3" required title="Two uppercase letters or ALL"></label><label>City code (optional)<input name="city" value="${esc(params.get('city')||'')}" pattern="[A-Z0-9_-]{2,10}" maxlength="10" placeholder="e.g. MAD"></label>`;
  $('filters').hidden=!html;$('filters').innerHTML=html+(html?'<button type="submit">Apply filters</button>':'');
}
async function request(path,signal){const response=await fetch(path,{cache:'no-store',signal});let data;try{data=await response.json();}catch{throw new Error('The server returned an unreadable response.');}if(!response.ok)throw new Error(data.error||'The query could not complete.');return data;}
async function load(){
  const id=++generation;comparisonGeneration++;controller?.abort();controller=new AbortController();
  $('refresh').disabled=true;$('analytics-error').hidden=true;$('analytics-content').setAttribute('aria-busy','true');$('analytics-status').textContent='Reading ClickHouse…';
  // Clear old results and timings before requesting a different scope.
  $('analytics-content').innerHTML='';$('query-list').innerHTML='';lastData=null;
  const selection=new URLSearchParams(location.search),params=new URLSearchParams();
  for(const key of ['kind','period','country','city'])if(selection.get(key))params.set(key,selection.get(key));
  const endpoint=['journey','performance'].includes(panel)?panel:'historical';
  if(endpoint==='historical')params.set('dataset',panel);
  try{
    const data=await request('/api/'+endpoint+(params.size?'?'+params:''),controller.signal);if(id!==generation)return;
    lastData=data;$('analytics-content').innerHTML=panel==='journey'?journey(data):panel==='performance'?performance(data):historical(data);queries(data);
    $('analytics-status').textContent='ClickHouse reads completed: '+(data.queried_at||'time unavailable')+' UTC. '+(panel==='journey'?'Shared refresh window: 5 seconds.':panel==='performance'?'Shared refresh window: 10 seconds.':'Shared refresh window: 60 seconds.');
    $('compare')?.addEventListener('click',compare);
  }catch(error){if(error.name==='AbortError'||id!==generation)return;$('analytics-error').hidden=false;$('analytics-error').textContent=error.message+' Check the host version and connection, then refresh this view.';$('analytics-status').textContent='No current snapshot. Previous figures and timings have been cleared.';}
  finally{if(id===generation){$('refresh').disabled=false;$('analytics-content').setAttribute('aria-busy','false');}}
}
async function compare(){
  const button=$('compare'),target=$('comparison'),workloadSelect=$('workload'),workload=workloadSelect.value,id=++comparisonGeneration;
  button.disabled=true;workloadSelect.disabled=true;target.textContent='Running the fixed '+workload.toUpperCase()+' queries in ClickHouse…';
  try{const data=await request('/api/benchmark?workload='+encodeURIComponent(workload),controller.signal);if(id!==comparisonGeneration||panel!=='performance')return;target.innerHTML=comparison(data);}
  catch(error){if(error.name!=='AbortError'&&id===comparisonGeneration)target.textContent='Comparison unavailable: '+error.message+' Refresh or choose a workload loaded on this host.';}
  finally{if(id===comparisonGeneration&&button.isConnected){button.disabled=false;workloadSelect.disabled=false;}}
}
function navigate(next,{push=true}={}){
  panel=names[next]?next:'journey';const url=new URL(location.href);url.search='';url.searchParams.set('panel',panel);if(push){history.pushState(null,'',url);window.scrollTo({top:0,left:0,behavior:'instant'});}
  $('panel-title').textContent=names[panel][0];$('panel-question').textContent=names[panel][1];document.title=names[panel][0]+' · ClickHouse · Delivery Atlas';
  document.querySelectorAll('[data-panel]').forEach(a=>{if(a.dataset.panel===panel)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});filters();load();
}
document.querySelectorAll('[data-panel]').forEach(a=>a.addEventListener('click',event=>{if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();navigate(a.dataset.panel);}));
$('filters').addEventListener('submit',event=>{event.preventDefault();const url=new URL(location.href);url.search='';url.searchParams.set('panel',panel);for(const [key,v]of new FormData($('filters')))if(v)url.searchParams.set(key,String(v));history.pushState(null,'',url);load();});
$('refresh').addEventListener('click',load);window.addEventListener('popstate',()=>navigate(new URLSearchParams(location.search).get('panel'),{push:false}));window.addEventListener('pagehide',()=>controller?.abort());
navigate(panel,{push:false});
