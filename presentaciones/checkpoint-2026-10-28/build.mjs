const C={paper:'#f6f7f3',ink:'#18242d',green:'#24553d',muted:'#52645b',soft:'#e7eee5',line:'#bdcbbd',blue:'#244e77',orange:'#96520d'};
function t(s,name,value,x,y,w,h,size=28,color=C.ink,bold=false){const a=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0},text:{text:value}});a.text.style={fontSize:size,typeface:'Arial',color,bold,insets:0,autoFit:'none',wrap:'square'};return a;}
function slide(p,c,i){const s=p.slides.add({width:1280,height:720});s.background.fill=C.paper;t(s,'headline',c.title,64,85,1150,112,47,C.ink,true);t(s,'speaker',c.speaker,64,677,1000,25,18,C.muted);t(s,'number',String(i+1).padStart(2,'0'),1160,675,50,28,20,C.muted);s.speakerNotes.text=c.speaker+' · '+Math.floor(c.seconds/60)+':'+String(c.seconds%60).padStart(2,'0')+'\n\n'+c.script+(c.actions?'\n\nDemo actions:\n'+c.actions.join('\n'):'')+'\n\nSources:\n'+c.sources.join('\n');return s;}
function foot(s,text){t(s,'footnote',text,64,615,1150,48,21,C.muted);}
function tab(s,values,widths,y,h,size=24){const a=s.tables.add({rows:values.length,columns:values[0].length,left:64,top:y,width:1150,height:h,columnWidths:widths,values});a.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.paper,textStyle:{fontSize:size,typeface:'Arial',color:C.ink},margins:{left:14,right:14,top:12,bottom:12}});a.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:C.soft,textStyle:{fontSize:size,typeface:'Arial',bold:true,color:C.green}});a.borders.assign({fill:C.line,width:.5});return a;}
function node(s,name,title,detail,x,y,w,h){const a=s.shapes.add({geometry:'rect',name,position:{left:x,top:y,width:w,height:h},fill:C.soft,line:{fill:C.line,width:1}});t(s,name+'-title',title,x+15,y+17,w-30,50,27,C.green,true);t(s,name+'-detail',detail,x+15,y+75,w-30,h-85,23);return a;}
function link(s,a,b){s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.green,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});}
export async function cover({presentation:p}){
 const s=p.slides.items.length?p.slides.getItem(0):p.slides.add({width:1280,height:720});
 if(s.shapes.items.length)return {cover:s.toSnapshot().aid};
 s.background.fill=C.ink;t(s,'section','BD2 · PROJECT CHECKPOINT',85,90,1080,45,21,'#91c2a5',true);t(s,'title','Delivery Atlas',85,258,1100,110,80,C.paper,true);t(s,'subtitle','ClickHouse for event analytics\nA fictional delivery platform in Madrid',85,380,1080,108,34,'#d1dbd3');t(s,'team','Geremi Contreras     Anuar Haddad     Echenique     Juanro',85,611,1110,40,25,'#d1dbd3');
 await p.render({slide:0});return {cover:s.toSnapshot().aid};
}
export async function build({presentation:p,input}){
const {slides:cs,start,end,assets}=input;
for(let i=start;i<end;i++){
 if(p.slides.items.length>i)continue;
 const c=cs[i],s=slide(p,c,i);
 if(i===1){
  [['100','fictional customers'],['50','simulated couriers'],['2 s','configured GPS interval']].forEach((r,j)=>{const x=64+j*390;t(s,'count-'+j,r[0],x,248,360,105,80,C.green,true);t(s,'count-label-'+j,r[1],x,361,355,75,28);});
  t(s,'question','How do we read current state and analyse event histories?',64,493,1120,88,36,C.ink,true);foot(s,'Configuration reported by Anuar · 28 October 2026. This is not a throughput measurement.');
 }
 if(i===2){
  [['Column-oriented storage','Read the columns needed by an analytical query.'],['SQL and analytical functions','Filter, join and aggregate over typed tables.'],['Workload fit','Batched ingestion and analytical reads; transaction guarantees depend on the operation.']].forEach((r,j)=>{const x=64+j*390;t(s,'concept-title-'+j,r[0],x,240,350,100,32,C.green,true);t(s,'concept-body-'+j,r[1],x,357,350,190,28);});foot(s,'Our demo uses one ClickHouse 25.8 node. It does not use a cross-system transaction.');
 }
 if(i===3){
  t(s,'sql','SELECT treatment, count(), avg(visit)\nFROM delivery.criteo_uplift\nGROUP BY treatment;',64,216,1120,125,31,C.green);
  tab(s,[['treatment','visit','conversion','exposure','feature columns'],['Read','Read','Not requested','Not requested','Not requested']],[210,155,230,230,325],367,132,23);
  t(s,'mechanisms','Sort order can skip granules. Batches become parts. Compression reduces bytes.',64,531,1150,63,29,C.ink,true);foot(s,'Logical column selection, not a PostgreSQL benchmark. Physical reads depend on the execution plan.');
 }
 if(i===4){
  t(s,'live-source','Fictional events · traffic, model decisions and mini-app',64,207,1150,40,27,C.green,true);
  const a=node(s,'api','Python API','Validate event\nand identity',64,274,195,176),b=node(s,'outbox','SQLite outbox','Commit accepted\nevents locally',303,274,205,176),d=node(s,'publisher','Publisher','Send batches\nto ClickHouse',552,274,205,176),e=node(s,'ch','ClickHouse','Histories and\naggregate states',801,274,205,176),f=node(s,'read','Read API','Latest views\nand dashboards',1050,274,165,176);
  link(s,a,b);link(s,b,d);link(s,d,e);link(s,e,f);
  t(s,'db-live','delivery_atlas · event histories → argMax states → latest-state reads',64,485,1150,45,28,C.green,true);
  t(s,'db-public','Public sources → batch loaders → delivery → historical summaries',64,554,1150,45,27,C.blue,true);foot(s,'One node. The durable outbox supports publication retries; it is not a replica or a backup.');
 }
 if(i===5){
  tab(s,[['Origin','What it contains','How we interpret it'],['Rule-based traffic','Fictional activity, fixed seed','Repeatable workload generation'],['Model decisions','Fictional customer choices','Recorded decisions, validated by Python'],['Public datasets','Criteo records; Glovo catalog','Separate populations and row meanings']],[260,435,455],231,322,25);foot(s,'Hybrid configuration: 3 model customers + 97 traffic customers. An AI configuration is not proof of a model call.');
 }
 if(i===6){
  s.background.fill=C.ink;s.shapes.items.find(x=>x.name==='headline').text.style={color:C.paper};s.shapes.items.find(x=>x.name==='speaker').text.style={color:'#c7d5ca'};s.shapes.items.find(x=>x.name==='number').text.style={color:'#c7d5ca'};
  s.images.add({path:assets.map,alt:'Recorded Madrid map from the supplied checkpoint; fictional courier positions on OpenStreetMap streets.',fit:'contain',position:{left:64,top:235,width:790,height:397}});
  t(s,'map-explain','Latest position',902,235,305,50,32,'#91c2a5',true);t(s,'map-current','argMax aggregate states\nOne current row per courier',902,303,305,110,27,C.paper);t(s,'map-history','Recorded path',902,442,305,48,32,'#91c2a5',true);t(s,'map-detail','A separate history read\nSamples, not road routing',902,510,305,100,27,C.paper);t(s,'recorded','Recorded fallback · supplied checkpoint, 28 Oct 2026 · use event time and age in the live demo',64,641,1140,28,20,'#c7d5ca');
 }
 if(i===7){
  t(s,'ai-label','AI decisions',64,208,540,45,31,C.blue,true);t(s,'data-label','Public-data summaries',655,208,540,45,31,C.orange,true);
  s.images.add({path:assets.ai,alt:'Recorded AI decision view from the supplied checkpoint.',fit:'contain',position:{left:64,top:268,width:540,height:244}});s.images.add({path:assets.datasets,alt:'Recorded Criteo and Glovo dashboard from the supplied checkpoint. Figures are sample summaries, not campaign incrementality.',fit:'contain',position:{left:655,top:268,width:540,height:244}});
  t(s,'reading','Check model state and call budget. Report query time, rows read and timestamp together.',64,538,1140,65,27,C.ink,true);foot(s,'Recorded fallback. Server execution time excludes browser/gateway time; shared responses may be cached.');
 }
 if(i===8){
  tab(s,[['Running core','Implemented in PR #9','Before the final talk'],['Event ingestion and map\nPublic-data views','Customer Journey\nClickHouse Performance','Deploy backend + gateway\nScratch-table CRUD rehearsal'],['One-node host\nRead-only sharing','Fixed SQL + read statistics\nTested; awaiting host rollout','Independent install check\nTimed four-person rehearsal']],[360,400,390],230,310,24);
  t(s,'limits','Limits: host and tunnel availability, finite model calls, eventual replacement of duplicate versions.',64,566,1150,70,27,C.ink,true);
 }
 if(i===9){
  s.background.fill=C.green;s.shapes.items.find(x=>x.name==='headline').text='ClickHouse in practice';s.shapes.items.find(x=>x.name==='headline').position={left:85,top:210,width:1110,height:90};s.shapes.items.find(x=>x.name==='headline').text.style={fontSize:64,color:C.paper};s.shapes.items.find(x=>x.name==='speaker').text.style={color:'#d1dbd3'};s.shapes.items.find(x=>x.name==='number').text.style={color:'#d1dbd3'};
  t(s,'closing','Connect the question to its data grain,\nstorage design and measured query cost.',85,333,1110,130,37,C.paper);t(s,'questions','Questions?',85,512,1100,55,32,'#c7dfce',true);t(s,'repo','github.com/Gere2/analitica-reparto-clickhouse',85,592,1120,40,24,'#c7dfce');
 }
}
await p.render({slide:Array.from({length:end-start},(_,i)=>start+i)});return {slides:p.slides.items.length,added:[start+1,end]};
}

export async function verifiedEvidence({presentation:p,input}){
 const v=input.verified_run;
 const config=p.slides.getItem(1);config.shapes.items.find(a=>a.name==='footnote').text='Configuration verified through the read API · 28 October 2026, 10:36 UTC. Not a throughput measurement.';
 const s=p.slides.getItem(7),keep=new Set(['headline','speaker','number']);
 p.delete([...s.shapes.items.filter(x=>!keep.has(x.name)),...s.images.items,...s.tables.items].map(x=>x.toSnapshot().aid));
 t(s,'ai-label','Model decisions',64,220,540,48,32,C.blue,true);t(s,'data-label','Criteo · observed read',655,220,540,48,32,C.orange,true);
 const a=tab(s,[['AI customers in this run','3'],['Model calls',v.model_calls+' / '+v.max_model_calls],['Model state','Limit reached'],['Confirmed checkouts','4']],[330,210],300,260,25);a.position={left:64,top:300,width:540,height:260};
 const b=s.tables.add({rows:4,columns:2,left:655,top:300,width:540,height:260,columnWidths:[290,250],values:[['Rows read','13,979,592'],['Server execution','105.7 ms'],['Result groups','2'],['Dataset','Released sample']]});b.cells.block({row:0,column:0,rowCount:4,columnCount:2}).assign({fill:C.paper,textStyle:{fontSize:25,typeface:'Arial',color:C.ink},margins:{left:14,right:14,top:12,bottom:12}});b.borders.assign({fill:C.line,width:.5});
 foot(s,'Verified 28 October 2026, 10:36 UTC. One read; server execution excludes browser/gateway latency.');
 if(input.recordedMap){const map=p.slides.getItem(6);map.images.items[0].replace({path:input.recordedMap,alt:'Recorded public demo, 28 October 2026, about 11:43 Europe/Madrid. Fictional couriers on OpenStreetMap streets.'});map.shapes.items.find(a=>a.name==='recorded').text='Recorded public demo · 28 Oct 2026, 11:43 Madrid · check event time and age during the live talk';}
 input.slides.forEach((c,i)=>{p.slides.getItem(i).speakerNotes.text=c.speaker+' · '+Math.floor(c.seconds/60)+':'+String(c.seconds%60).padStart(2,'0')+'\n\n'+c.script+(c.actions?'\n\nDemo actions:\n'+c.actions.join('\n'):'')+'\n\nSources:\n'+c.sources.join('\n');});
 await p.render();return {slides:p.slides.items.length,verifiedRun:v.run_id};
}
