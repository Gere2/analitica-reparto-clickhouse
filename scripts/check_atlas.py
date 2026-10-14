"""Integration evidence: repeated HTTP request and ambiguous ClickHouse acknowledgement."""
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atlas.clickhouse import ClickHouse
from atlas.contract import validate
from atlas.store import Store
from atlas.server import Publisher
from scripts.atlas import call

def main():
    ch=ClickHouse();ch.init()
    run=str(uuid4())
    base={'schema_version':1,'event_id':str(uuid4()),'session_id':str(uuid4()),
          'event_time':datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
          'event_type':'search','section':'integration-check','city_id':'test-city',
          'source':'integration-check','source_kind':'synthetic','simulation_run_id':run}
    payload={'events':[base]}
    first=call('http://127.0.0.1:8001','/api/events',payload)
    retry=call('http://127.0.0.1:8001','/api/events',payload)
    assert first['accepted']==1 and retry['accepted']==0 and retry['duplicates']==1
    try:
        call('http://127.0.0.1:8001','/api/events',{'events':[dict(base,city_id='different')]})
        raise AssertionError('Conflicto no rechazado')
    except HTTPError as error:
        assert error.code==409
    try:
        call('http://127.0.0.1:8001','/api/events',{'events':[dict(base,event_id=str(uuid4()),event_type='invalid')]})
        raise AssertionError('Contrato inválido aceptado')
    except HTTPError as error:
        assert error.code==400
    event_id=base['event_id']
    for _ in range(30):
        rows=ch.query(f"SELECT count() AS n FROM delivery_atlas.app_events FINAL WHERE event_id='{event_id}'")
        if int(rows[0]['n'])==1:
            break
        time.sleep(1)
    else:
        raise AssertionError('El evento no se publicó')
    # Simulate a lost acknowledgement after ClickHouse accepted the block.
    second=dict(base,event_id=str(uuid4()))
    with tempfile.TemporaryDirectory() as tmp:
        local=Store(tmp+'/outbox.sqlite')
        local.accept([validate(second)])
        rows=local.pending(5000)
        ch.publish([p for _,p in rows])  # deliberately do not mark the local journal
        restored=Store(tmp+'/outbox.sqlite')
        Publisher(restored,ch).once()   # replay after restart
        assert restored.status()['pending']==0
    raw=ch.query("SELECT count() AS n FROM delivery_atlas.app_events WHERE simulation_run_id={run:UUID}",{'param_run':run})[0]
    logical=ch.query("SELECT count() AS n FROM delivery_atlas.app_events FINAL WHERE simulation_run_id={run:UUID}",{'param_run':run})[0]
    detail=ch.query('SELECT event_date,city_id,section,event_type,source_kind,count() AS events '
                    'FROM delivery_atlas.app_events FINAL GROUP BY event_date,city_id,section,event_type,source_kind '
                    'ORDER BY event_date,city_id,section,event_type,source_kind')
    aggregate=ch.query('SELECT event_date,city_id,section,event_type,source_kind,events '
                      'FROM delivery_atlas.app_daily_counts ORDER BY event_date,city_id,section,event_type,source_kind')
    assert detail==aggregate, 'Histórico y agregado no coinciden'
    assert int(logical['n'])==2
    output={'checked_at':datetime.now(timezone.utc).isoformat(),'run_id':run,
            'http_retry':retry,'conflict_status':409,'invalid_status':400,
            'physical_rows_for_test':int(raw['n']),'logical_events_for_test':int(logical['n']),
            'ambiguous_acknowledgement_replayed':True,'detail_matches_rollup':True,
            'scope':'Prueba local del recorrido y reintentos, no garantía de entrega exactamente una vez.'}
    dest=ROOT/'data/atlas';dest.mkdir(parents=True,exist_ok=True)
    (dest/'checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
