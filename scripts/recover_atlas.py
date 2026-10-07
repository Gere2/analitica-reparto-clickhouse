"""Local recovery exercise. Stops/restarts the demo services; never deletes volumes."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.atlas import call
from atlas.clickhouse import ClickHouse

def docker(*args):
    subprocess.run(['docker','compose','-f','compose.yaml','--profile','atlas',*args],cwd=ROOT,check=True)

def main():
    before=call('http://127.0.0.1:8001','/api/status')
    if before['pending']:
        raise SystemExit('Esperar a pending=0 y detener generadores antes de esta prueba.')
    event={'schema_version':1,'event_id':str(uuid4()),'session_id':str(uuid4()),
           'event_time':datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
           'event_type':'search','section':'recovery-check','city_id':'test-city',
           'source':'recovery-check','source_kind':'demo_live'}
    restored=False
    try:
        docker('stop','clickhouse')
        accepted=call('http://127.0.0.1:8001','/api/events',{'events':[event]})
        pending=call('http://127.0.0.1:8001','/api/status')
        assert accepted['accepted']==1 and pending['pending']==1
        docker('stop','atlas')
        docker('up','-d','--build','--wait')
        restored=True
        ch=ClickHouse()
        for _ in range(30):
            n=int(ch.query('SELECT count() AS n FROM delivery_atlas.app_events FINAL '
                           'WHERE event_id={id:UUID}',{'param_id':event['event_id']})[0]['n'])
            if n==1:
                break
            time.sleep(1)
        else:
            raise AssertionError('El evento pendiente no se recuperó')
        retry=call('http://127.0.0.1:8001','/api/events',{'events':[event]})
        assert retry['duplicates']==1 and retry['accepted']==0
        output={'checked_at':datetime.now(timezone.utc).isoformat(),'event_id':event['event_id'],
                'accepted_during_database_outage':True,'pending_before_api_restart':pending['pending'],
                'logical_count_after_recovery':n,'retry_after_restart':retry,
                'final_status':call('http://127.0.0.1:8001','/api/status'),
                'scope':'Parada ordenada de servicios locales y persistencia de volúmenes. No prueba pérdida de disco ni caída abrupta del sistema.'}
        path=ROOT/'data/atlas/recovery.json'
        path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(output,ensure_ascii=False,indent=2))
    finally:
        if not restored:
            docker('up','-d','--build','--wait')

if __name__=='__main__':
    main()
