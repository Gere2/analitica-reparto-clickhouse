const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');

function ui(){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',hidden:false,disabled:false,setAttribute(){}});return nodes.get(id);};
  const context=vm.createContext({Intl,URLSearchParams,URL,AbortController,console,
    location:{search:'?panel=journey',href:'http://validation.invalid/analytics.html?panel=journey'},
    document:{getElementById:node},module:{exports:{}}});
  const source=readFileSync(join(__dirname,'../web/analytics.js'),'utf8').split("document.querySelectorAll('[data-panel]').forEach(a=>a.addEventListener")[0];
  vm.runInContext(source+'\nmodule.exports={journey,comparison,bars,historical,queries};',context);
  return {app:context.module.exports,node};
}
test('empty cohort is unavailable rather than NaN or an invented zero-percent conversion',()=>{
  const {app}=ui();const html=app.journey({available:true,cohort_sessions:0,abandoned_sessions:0,excluded_sessions:0,run_id:'test',kind:'all',steps:[{label:'Session',sessions:0,share_pct:null}],actions:[],timeline:[],definition:'Test',classification:'Test'});
  assert.match(html,/No cohort/);assert.doesNotMatch(html,/NaN|Infinity/);
});
test('a mismatched aggregate cannot display an optimisation ratio and SQL is escaped',()=>{
  const {app}=ui();const query={label:'<script>not markup</script>',elapsed_ms:1,rows_read:2,bytes_read:4,sql:'SELECT <literal>'};
  const html=app.comparison({available:true,same_result:false,scope:'Test',detail:query,aggregate:query,result_groups:1,logical_events:2,ratio:null,definition:'Test'});
  assert.match(html,/Answers differ/);assert.doesNotMatch(html,/Observed detail \/ aggregate time ratio|<script>|<literal>/);assert.match(html,/&lt;literal&gt;/);
});
test('missing historical dataset provides an honest host dependency rather than fixture figures',()=>{
  const {app}=ui();const html=app.historical({available:false,message:'Load this dataset on the host',table:'delivery.otto_archive'});
  assert.match(html,/Load this dataset on the host/);assert.match(html,/delivery.otto_archive/);assert.doesNotMatch(html,/216,716,096/);
});
test('query evidence displays actual server statistics and parameterised SQL',()=>{
  const {app,node}=ui();app.queries({queries:[{label:'Counts',elapsed_ms:2,rows_read:8,bytes_read:64,sql:'WHERE simulation_run_id={run:UUID}'}]});
  assert.match(node('query-list').innerHTML,/2 ms/);assert.match(node('query-list').innerHTML,/8 rows read/);assert.match(node('query-list').innerHTML,/\{run:UUID\}/);
});
