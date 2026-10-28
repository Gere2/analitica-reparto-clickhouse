'use strict';
const routes = new Set(['simulation','operations','status','track','summary','inventory','catalog','datasets','journey','performance','benchmark','historical']);
module.exports = async (req, res) => {
  res.setHeader('Cache-Control','no-store');
  if(req.method !== 'GET') return res.status(405).json({error:'The shared demo is read-only'});
  const query = new URL(req.url, 'https://atlas.invalid').searchParams;
  const endpoint = req.query?.endpoint || query.get('endpoint') || req.url.split('?')[0].replace('/api/','');
  if(!routes.has(endpoint)) return res.status(404).json({error:'Route not available'});
  const origin = process.env.ATLAS_SHARE_ORIGIN;
  const token = process.env.ATLAS_SHARE_TOKEN;
  if(!origin || !token) return res.status(503).json({error:'The connection to the lab is not configured yet'});
  try {
    const base = new URL(origin);
    if(base.protocol !== 'https:' || !base.hostname.endsWith('.trycloudflare.com')) throw new Error('Invalid origin');
    const target = new URL('/api/' + endpoint, base);
    const allowed = new Set(({track:['run_id','courier_id'],summary:['city_id','source_kind'],journey:['run_id','kind'],benchmark:['workload'],historical:['dataset','period','country','city']})[endpoint]||[]);
    for(const [key,value] of query) {
      if(key==='endpoint') continue;
      if(!allowed.has(key) || target.searchParams.has(key)) return res.status(400).json({error:'Parameters not available'});
      target.searchParams.set(key,value);
    }
    const p=target.searchParams,invalid=()=>res.status(400).json({error:'Analytical filter not available'});
    if(endpoint==='journey'&&((p.has('kind')&&!['all','ai','simulated'].includes(p.get('kind')))||(p.has('run_id')&&!/^[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12}$/i.test(p.get('run_id')))))return invalid();
    if(endpoint==='benchmark'&&p.has('workload')&&!['atlas','otto'].includes(p.get('workload')))return invalid();
    if(endpoint==='historical'){
      const dataset=p.get('dataset')||'otto';
      if(!['otto','rees46','eleme','glovo','criteo'].includes(dataset))return invalid();
      if(p.has('period')&&(!['rees46','eleme'].includes(dataset)||!(dataset==='rees46'?['ALL','201910','201911','201912','202001','202002','202003','202004']:['ALL','1','2','3','4','5','6','7','8']).includes(p.get('period'))))return invalid();
      if((p.has('country')||p.has('city'))&&dataset!=='glovo')return invalid();
      if(p.has('country')&&!/^(ALL|[A-Z]{2})$/.test(p.get('country')))return invalid();
      if(p.has('city')&&((p.get('country')||'ES')==='ALL'||! /^[A-Z0-9_-]{2,10}$/.test(p.get('city'))))return invalid();
    }
    const analytical=['journey','performance','benchmark','historical'].includes(endpoint);
    const response = await fetch(target,{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(analytical?25000:12000),redirect:'error'});
    if(!response.ok) return res.status(503).json({error:'The demo server is not available. It will be retried.'});
    res.status(200).json(await response.json());
  } catch(error) {
    res.status(503).json({error:'The demo server is not available. It will be retried.'});
  }
};
