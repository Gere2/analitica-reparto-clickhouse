"""Live HTTP/ClickHouse checks, isolated run. No fleet simulation is started."""
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas.clickhouse import ClickHouse
from atlas.simulation import Scenario,iso
from atlas.store import Store
from atlas.server import Publisher

BASE='http://127.0.0.1:8001'
def send(kind,rows):
    payload={'kind':kind,'events':[{k:v for k,v in row.items() if k!='_stream'} for row in rows]}
    with urlopen(Request(BASE+'/api/operations',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=30) as response:
        return response.status,json.load(response)

def until(fn):
    end=time.monotonic()+40
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.5)
    raise RuntimeError('Tiempo agotado esperando publicación.')

def main():
    ch=ClickHouse()
    run=str(uuid4())
    at=datetime.now(timezone.utc)-timedelta(seconds=35)
    gps,orders,_=Scenario(run,at,3,42).sample(at)
    status,accepted=send('courier_positions',gps)
    assert status==202 and accepted['accepted']==3
    status,duplicate=send('courier_positions',gps)
    assert status==200 and duplicate['duplicates']==3
    send('order_events',orders)
    until(lambda:len(ch.operations(run)['couriers'])==3 and len(ch.operations(run)['orders'])==3)
    latest=dict(gps[0],event_id=str(uuid4()),event_time=iso(at+timedelta(seconds=25)),latitude=gps[0]['latitude']+.001)
    older=dict(gps[0],event_id=str(uuid4()),event_time=iso(at+timedelta(seconds=10)),latitude=gps[0]['latitude']-.001)
    send('courier_positions',[latest])
    send('courier_positions',[older])
    params={'param_run':run,'param_courier':gps[0]['courier_id']}
    until(lambda: int(ch.query('SELECT uniqExact(event_id) AS n FROM delivery_atlas.courier_positions WHERE simulation_run_id={run:UUID}',{'param_run':run})[0]['n'])==5)
    row=ch.query('SELECT latitude,event_time FROM delivery_atlas.courier_latest WHERE simulation_run_id={run:UUID} AND courier_id={courier:UUID}',params)[0]
    assert abs(row['latitude']-latest['latitude'])<1e-9, row
    invalid=dict(gps[0],event_id=str(uuid4()),latitude=95)
    try:send('courier_positions',[invalid])
    except HTTPError as error:assert error.code==400
    else:raise AssertionError('GPS fuera de rango aceptado')

    # A failure after first table INSERT leaves the whole mixed batch pending.
    mixed_run=str(uuid4())
    mixed_gps,mixed_orders,_=Scenario(mixed_run,at,2,42).sample(at)
    class FailSecondInsert(ClickHouse):
        def execute(self,sql,params=None):
            if sql.startswith('INSERT INTO delivery_atlas.order_events'):
                raise OSError('Fallo inyectado después de insertar posiciones')
            return super().execute(sql,params)
    with tempfile.TemporaryDirectory() as temp:
        store=Store(temp+'/outbox.sqlite')
        store.accept(mixed_gps+mixed_orders)
        try:Publisher(store,FailSecondInsert()).once()
        except OSError:pass
        else:raise AssertionError('No se inyectó el fallo esperado')
        assert store.status()['pending']==4
        Publisher(Store(store.path),ch).once()
        assert Store(store.path).status()['pending']==0
    rows=ch.query('SELECT count() AS physical,uniqExact(event_id) AS logical FROM delivery_atlas.courier_positions WHERE simulation_run_id={run:UUID}',{'param_run':mixed_run})[0]
    assert int(rows['logical'])==2 and int(rows['physical'])>=2
    snapshot=ch.operations(mixed_run)
    assert len(snapshot['couriers'])==2 and int(snapshot['metrics']['orders'])==2
    report={'checked_at':iso(datetime.now(timezone.utc)),'run_id':run,'http_retry':duplicate,
        'out_of_order_keeps_latest':True,'invalid_coordinates_status':400,
        'mixed_batch_recovers':True,'mixed_run':mixed_run,'logical_positions_after_replay':int(rows['logical']),
        'physical_positions_after_replay':int(rows['physical']),
        'latest_couriers_after_replay':len(snapshot['couriers']),'logical_orders_after_replay':int(snapshot['metrics']['orders']),
        'scope':'Prueba local con fallo inyectado entre INSERTs. No transacción entre tablas ni GPS observado.'}
    path=Path(__file__).resolve().parents[1]/'docs/evidencia-tracking.json'
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
