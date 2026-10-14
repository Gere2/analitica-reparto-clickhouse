'use strict';
const routes = new Set(['simulation','operations','status','track','summary','inventory','catalog']);
module.exports = async (req, res) => {
  res.setHeader('Cache-Control','no-store');
  if(req.method !== 'GET') return res.status(405).json({error:'La demo compartida es de solo lectura'});
  const query = new URL(req.url, 'https://atlas.invalid').searchParams;
  const endpoint = req.query?.endpoint || query.get('endpoint') || req.url.split('?')[0].replace('/api/','');
  if(!routes.has(endpoint)) return res.status(404).json({error:'Ruta no disponible'});
  const origin = process.env.ATLAS_SHARE_ORIGIN;
  const token = process.env.ATLAS_SHARE_TOKEN;
  if(!origin || !token) return res.status(503).json({error:'La conexión con el laboratorio todavía no está configurada'});
  try {
    const base = new URL(origin);
    if(base.protocol !== 'https:' || !base.hostname.endsWith('.trycloudflare.com')) throw new Error('Invalid origin');
    const target = new URL('/api/' + endpoint, base);
    const allowed = endpoint==='track' ? new Set(['run_id','courier_id']) : endpoint==='summary' ? new Set(['city_id','source_kind']) : new Set();
    for(const [key,value] of query) {
      if(key==='endpoint') continue;
      if(!allowed.has(key) || target.searchParams.has(key)) return res.status(400).json({error:'Parámetros no disponibles'});
      target.searchParams.set(key,value);
    }
    const response = await fetch(target,{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(12000),redirect:'error'});
    if(!response.ok) return res.status(503).json({error:'El laboratorio de Jere no está disponible. Se reintentará.'});
    res.status(200).json(await response.json());
  } catch(error) {
    res.status(503).json({error:'El laboratorio de Jere no está disponible. Se reintentará.'});
  }
};
