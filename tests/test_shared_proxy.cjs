const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
function fixture(){
  const calls=[],context=vm.createContext({module:{exports:{}},URL,AbortSignal,
    process:{env:{ATLAS_SHARE_ORIGIN:'https://validation-only.trycloudflare.com',ATLAS_SHARE_TOKEN:'test-only-server-token'}},
    fetch:async(url,options)=>{calls.push({url:String(url),options});return{ok:true,json:async()=>({criteo:null,glovo:null})};}});
  vm.runInContext(readFileSync(join(__dirname,'../api/proxy.js'),'utf8'),context);
  const response={code:200,headers:{},setHeader(k,v){this.headers[k]=v;},status(code){this.code=code;return this;},json(body){this.body=body;return this;}};
  return {proxy:context.module.exports,response,calls};
}
test('downloaded datasets cross the server proxy as an authenticated read without exposing credentials',async()=>{
  const {proxy,response,calls}=fixture();await proxy({method:'GET',query:{endpoint:'datasets'},url:'/api/datasets'},response);
  assert.equal(response.code,200);assert.equal(calls[0].url,'https://validation-only.trycloudflare.com/api/datasets');assert.equal(calls[0].options.headers.Authorization,'Bearer test-only-server-token');
  assert.doesNotMatch(JSON.stringify(response),/test-only-server-token/);assert.equal(response.headers['Cache-Control'],'no-store');
});
for(const [name,request,code] of [
  ['dataset SQL parameters',{method:'GET',query:{endpoint:'datasets'},url:'/api/datasets?sql=SELECT%201'},400],
  ['dataset writes',{method:'POST',query:{endpoint:'datasets'},url:'/api/datasets'},405],
  ['unlisted database routes',{method:'GET',query:{endpoint:'play'},url:'/api/play'},404]
])test('proxy rejects '+name+' before contacting the server',async()=>{
  const {proxy,response,calls}=fixture();await proxy(request,response);assert.equal(response.code,code);assert.equal(calls.length,0);
});
for(const endpoint of ['journey?kind=ai','performance','benchmark?workload=atlas','historical?dataset=glovo&country=ES&city=MAD'])test('analytical read is forwarded: '+endpoint,async()=>{
  const {proxy,response,calls}=fixture();await proxy({method:'GET',query:{endpoint:endpoint.split('?')[0]},url:'/api/'+endpoint},response);
  assert.equal(response.code,200);assert.equal(calls.length,1);assert.match(calls[0].url,/validation-only\.trycloudflare\.com\/api\//);
});
for(const endpoint of ['performance?sql=SELECT+1','journey?kind=all&kind=ai','journey?run_id=no','benchmark?workload=system.users','historical?dataset=otto&period=ALL','historical?dataset=glovo&country=ALL&city=MAD'])test('analytical filters reject unsafe or incompatible scope: '+endpoint,async()=>{
  const {proxy,response,calls}=fixture();await proxy({method:'GET',query:{endpoint:endpoint.split('?')[0]},url:'/api/'+endpoint},response);
  assert.equal(response.code,400);assert.equal(calls.length,0);
});
