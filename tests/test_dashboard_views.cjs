const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {webcrypto}=require('node:crypto');
const vm=require('node:vm');

function fixture(){
  class Element{
    constructor(){this.options=[];this.dataset={};this.textContent='';this.innerHTML='';this.attrs={};}
    addEventListener(){}
    replaceChildren(...rows){this.options=rows;}
    setAttribute(key,value){this.attrs[key]=value;}
  }
  const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
  const urls=[],mapUpdates=[];
  const ctx=vm.createContext({crypto:webcrypto,console,URL,URLSearchParams,
    location:{href:'https://atlas.example/?view=ai#tracking',search:'?view=ai'},
    history:{replaceState:(_,__,url)=>urls.push(String(url))},
    document:{getElementById:node,querySelector:selector=>selector.startsWith('meta')?{}:new Element(),querySelectorAll:()=>[]},
    window:{},mapUpdate:data=>mapUpdates.push(data.run_id)});
  const source=readFileSync(join(__dirname,'../web/atlas-dashboard.js'),'utf8');
  const bootstrap=source.indexOf('const fleetMap=new AtlasFleetMap');assert.ok(bootstrap>0);
  vm.runInContext(source.slice(0,bootstrap)+"\nconst fleetMap={update:mapUpdate,setHistory(){}};",ctx);
  const app=vm.runInContext('({renderOperations,renderDatasets,setView,configure:(sim,next)=>{lastSimulation=sim;view=next;},cacheDatasets:()=>{datasetsAt=Date.now();}})',ctx);
  return {app,node,urls,mapUpdates};
}
const totals={orders:8,active:3,delivered:5,delivered_amount_minor:9000};
const old={run_id:'run',metrics:totals,customer_metrics:{sessions:20,clicks:100,checkouts:8},couriers:[],customers:[],orders:[]};
test('old traffic server never shows simulated totals as AI activity',()=>{
  const {app,node}=fixture();app.configure({run_id:'run',mode:'customers',agent_mode:'traffic'},'ai');app.renderOperations(old);
  assert.equal(node('active').textContent,'0');assert.equal(node('customer-checkouts').textContent,'0');
  app.setView('simulated');assert.equal(node('active').textContent,'3');assert.equal(node('customer-checkouts').textContent,'8');
});
test('old mixed server reports missing split metrics rather than attributing all orders to one type',()=>{
  const {app,node}=fixture();app.configure({run_id:'run',mode:'customers',agent_mode:'hybrid'},'ai');app.renderOperations(old);
  assert.equal(node('active').textContent,'—');assert.equal(node('amount').textContent,'—');assert.equal(node('customer-sessions').textContent,'—');assert.equal(node('metrics-note').hidden,false);
  app.setView('simulated');assert.equal(node('active').textContent,'—');
});
test('switching among new views keeps map updates and the tracking link while metrics stay separate',()=>{
  const {app,node,urls,mapUpdates}=fixture();app.configure({run_id:'run',mode:'customers',agent_mode:'hybrid'},'ai');
  app.renderOperations({...old,metrics_by_kind:{ai:{active:1},simulated:{active:2}},customer_metrics_by_kind:{ai:{checkouts:1},simulated:{checkouts:7}}});
  assert.equal(node('active').textContent,'1');app.cacheDatasets();app.setView('real');assert.equal(node('live-view').hidden,true);
  app.setView('simulated');assert.equal(node('live-view').hidden,false);assert.equal(node('active').textContent,'2');assert.equal(node('customer-checkouts').textContent,'7');
  assert.equal(new URL(urls.at(-1)).hash,'#tracking');assert.equal(new URL(urls.at(-1)).searchParams.get('view'),'simulated');assert.equal(mapUpdates.length,2);
});
test('new run metadata cannot relabel totals returned for a previous run',()=>{
  const {app,node}=fixture();app.configure({run_id:'new-run',mode:'customers',agent_mode:'traffic'},'simulated');app.renderOperations(old);assert.equal(node('active').textContent,'—');
});
test('zero or missing Criteo control rates never produce Infinity or NaN in the UI',()=>{
  const {app,node}=fixture();const render=rows=>app.renderDatasets({criteo:{rows,rows_read:2,elapsed_ms:1},glovo:null,queried_at:'2026-10-21 15:00:00'});
  render([{treatment:0,users:1,visit_rate:0,conversion_rate:0},{treatment:1,users:1,visit_rate:.5,conversion_rate:.1}]);
  assert.doesNotMatch(node('criteo-body').innerHTML,/Infinity|NaN/);assert.match(node('criteo-body').innerHTML,/Observed difference/);
  render([{treatment:1,users:1,visit_rate:.5,conversion_rate:.1}]);assert.doesNotMatch(node('criteo-body').innerHTML,/Infinity|NaN/);
});
