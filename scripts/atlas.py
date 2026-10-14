"""Small reproducible load. Uses only the standard library and the Atlas API."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import UUID, uuid5, NAMESPACE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atlas.clickhouse import ClickHouse

def call(url, path, data=None):
    request = Request(url.rstrip('/')+path, data=None if data is None else json.dumps(data).encode(),
                      headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=60) as response:
        return json.load(response)

def event(i, run, start, seed):
    session = i // 5
    city = ('madrid','barcelona','valencia')[(session+seed)%3]
    restaurant = 'fictional-'+city+'-'+str((session+seed)%12)
    action = ('search','restaurant_opened','product_opened','cart_added','order_submitted')[i%5]
    return {'schema_version':1, 'event_id':str(uuid5(run, f'event-{i}')),
            'session_id':str(uuid5(run, f'session-{session}')),
            'event_time':(start+timedelta(milliseconds=i)).isoformat(timespec='milliseconds'),
            'event_type':action, 'section':('search','restaurants','products','cart','checkout')[i%5],
            'city_id':city, 'restaurant_id':restaurant if action!='search' else None,
            'product_id':restaurant+'-product-1' if action in {'product_opened','cart_added'} else None,
            'source':'atlas-generator', 'source_kind':'synthetic', 'simulation_run_id':str(run)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init','status','generate'])
    parser.add_argument('--url',default='http://127.0.0.1:8001')
    parser.add_argument('--events',type=int,default=10000)
    parser.add_argument('--batch',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--run-id')
    parser.add_argument('--start')
    parser.add_argument('--rate',type=float,default=0,help='Meta de eventos/s. 0 envía sin pausa.')
    args=parser.parse_args()
    if args.command=='init':
        ClickHouse().init()
        print('SQL delivery_atlas aplicado de forma idempotente.')
        return
    if args.command=='status':
        print(json.dumps(call(args.url,'/api/status'),indent=2))
        print(json.dumps(call(args.url,'/api/summary'),indent=2))
        return
    if args.events < 1 or not 1 <= args.batch <= 5000 or args.rate < 0:
        parser.error('events > 0; batch entre 1 y 5000; rate >= 0')
    start=datetime.fromisoformat(args.start.replace('Z','+00:00')) if args.start else datetime.now(timezone.utc)-timedelta(days=1)
    if start.tzinfo is None:
        parser.error('--start debe incluir zona horaria.')
    start=start.astimezone(timezone.utc).replace(microsecond=(start.microsecond//1000)*1000)
    run=UUID(args.run_id) if args.run_id else uuid5(NAMESPACE_URL, f'atlas:{args.seed}:{start.isoformat()}:{args.events}')
    clock=time.monotonic()
    accepted=duplicates=0
    digest=hashlib.sha256()
    for offset in range(0,args.events,args.batch):
        rows=[event(i,run,start,args.seed) for i in range(offset,min(offset+args.batch,args.events))]
        digest.update(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':')) for r in rows)+'\n').encode())
        payload={'events':rows}
        # Exact payload is reused. A transport error must never create fresh IDs.
        for attempt in range(10):
            try:
                result=call(args.url,'/api/events',payload)
                break
            except OSError as error:
                if getattr(error,'code',None) in {400,409,413} or attempt==9:
                    raise
                time.sleep(min(2**attempt,5))
        accepted+=result['accepted'];duplicates+=result['duplicates']
        if args.rate:
            time.sleep(max(0,(offset+len(rows))/args.rate-(time.monotonic()-clock)))
    elapsed=time.monotonic()-clock
    out=ROOT/'data/atlas';out.mkdir(parents=True,exist_ok=True)
    manifest={'run_id':str(run),'start':start.isoformat(timespec='milliseconds'),'seed':args.seed,
              'events':args.events,'batch':args.batch,'target_rate':args.rate,'accepted':accepted,
              'duplicates':duplicates,'submission_seconds':round(elapsed,4),
              'submitted_events_per_second':round(args.events/elapsed,2),'logical_payload_sha256':digest.hexdigest(),
              'source_kind':'synthetic','published_status':call(args.url,'/api/status'),
              'assumptions':'Catálogo y sesiones ficticios. Cada sesión tiene cinco acciones sin abandono. No es conversión real. Horas simuladas, no clics observados.'}
    path=out/(str(run)+'.json');path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Manifiesto:',path)
    print('Reproducir con el mismo --run-id, --start, --seed y --events. Esperar a pending=0 antes de medir consultas.')

if __name__=='__main__':
    main()
