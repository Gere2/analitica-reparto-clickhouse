'use strict';
const routes = new Set(['simulation','operations','status','track','summary','inventory','catalog','datasets']);
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
    const allowed = endpoint==='track' ? new Set(['run_id','courier_id']) : endpoint==='summary' ? new Set(['city_id','source_kind']) : new Set();
    for(const [key,value] of query) {
      if(key==='endpoint') continue;
      if(!allowed.has(key) || target.searchParams.has(key)) return res.status(400).json({error:'Parameters not available'});
      target.searchParams.set(key,value);
    }
    const response = await fetch(target,{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(12000),redirect:'error'});
    if(!response.ok) return res.status(503).json({error:'The demo server is not available. It will be retried.'});
    res.status(200).json(await response.json());
  } catch(error) {
    res.status(503).json({error:'The demo server is not available. It will be retried.'});
  }
};
