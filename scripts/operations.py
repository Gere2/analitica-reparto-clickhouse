"""Generate a reproducible historical GPS scenario through the real ingestion API."""
import argparse
import json
import sys
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas.simulation import Scenario,iso

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--positions',type=int,default=10000)
    parser.add_argument('--fleet',type=int,default=12)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--start',default='2026-10-06T10:00:00Z')
    args=parser.parse_args()
    start=datetime.fromisoformat(args.start.replace('Z','+00:00'))
    if start.tzinfo is None or not 1<=args.fleet<=50 or not 1<=args.positions<=10000000:
        parser.error('Fecha con zona, 1 a 50 repartidores, 1 a 10000000 posiciones.')
    ticks=(args.positions+args.fleet-1)//args.fleet
    if start+timedelta(seconds=(ticks-1)*2)>datetime.now(timezone.utc):
        parser.error('La fecha final simulada no puede ser futura; usar una fecha inicial anterior.')
    run=str(uuid5(NAMESPACE_URL,f'atlas-gps:{iso(start)}:{args.seed}:{args.fleet}:{args.positions}'))
    scenario=Scenario(run,start,args.fleet,args.seed)
    buffers={'courier_positions':[],'order_events':[]}
    counts={kind:0 for kind in buffers}
    counters={'accepted':0,'duplicates':0}
    begin=time.monotonic()
    def flush(kind):
        rows=buffers[kind]
        if not rows:return
        raw=json.dumps({'kind':kind,'events':[{k:v for k,v in row.items() if k!='_stream'} for row in rows]}).encode()
        # Every retry sends identical bytes/IDs. Permanent contract errors stop the load.
        from urllib.error import HTTPError,URLError
        for attempt in range(30):
            try:
                with urlopen(Request('http://127.0.0.1:8001/api/operations',data=raw,headers={'Content-Type':'application/json'}),timeout=60) as response:
                    result=json.load(response)
                break
            except HTTPError as error:
                if error.code!=503:raise
                if attempt==29:raise
                time.sleep(2)
            except (OSError,TimeoutError):
                if attempt==29:raise
                time.sleep(2)
        for key in counters:counters[key]+=result[key]
        counts[kind]+=len(rows)
        buffers[kind]=[]
    remaining=args.positions
    for tick in range(ticks):
        gps,orders,_=scenario.sample(start+timedelta(seconds=tick*2))
        included=gps[:remaining]
        buffers['courier_positions'].extend(included)
        couriers={p['courier_id'] for p in included}
        buffers['order_events'].extend(o for o in orders if o['courier_id'] in couriers)
        remaining-=len(included)
        for kind in buffers:
            if len(buffers[kind])>=4000:flush(kind)
    for kind in buffers:flush(kind)
    report={'run_id':run,'start':iso(start),'seed':args.seed,'fleet':args.fleet,'counts':counts,
        **counters,'submission_seconds':round(time.monotonic()-begin,3),'source_kind':'synthetic',
        'meaning':'Simulación histórica enviada por API; verificar publicación por run_id. No posiciones observadas.'}
    path=Path(__file__).resolve().parents[1]/'data/atlas'/f'gps-{run}.json'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
