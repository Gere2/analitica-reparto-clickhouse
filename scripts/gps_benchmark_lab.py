"""Load an existing GPS CSV or a tiny fixture into the marked separate lab only."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener
from uuid import UUID, uuid4, uuid5

from gps_benchmark import Client, LAB_URL, NoRedirect, ROOT, marker

GPS_COLUMNS = {'schema_version','event_id','simulation_run_id','event_time','ingested_at',
               'city_id','courier_id','order_id','latitude','longitude','speed_kmh','accuracy_m','source','source_kind'}


def admin_client():
    return Client(user=os.environ.get('GPS_LAB_ADMIN_USER','gps_lab_admin'),
                  password=os.environ.get('GPS_LAB_ADMIN_PASSWORD','gps-lab-admin-only'))


def inspect_csv(path, run_id, expected_rows):
    opener = gzip.open if path.suffix=='.gz' else open
    couriers, count = set(), 0
    with opener(path,'rt',encoding='utf-8',newline='') as stream:
        reader=csv.reader(stream)
        header=next(reader)
        if len(header)!=len(GPS_COLUMNS) or set(header)!=GPS_COLUMNS:
            raise ValueError('Expected exactly the courier_positions CSVWithNames columns.')
        positions={name:header.index(name) for name in header}
        for row in reader:
            count+=1
            if len(row)!=len(header) or row[positions['simulation_run_id']]!=run_id:
                raise ValueError(f'Wrong row length or simulation_run_id at CSV record {count}.')
            if row[positions['city_id']]!='madrid':
                raise ValueError('This first corpus must contain only Madrid positions.')
            couriers.add(str(UUID(row[positions['courier_id']])))
            for name,low,high in (('latitude',-90,90),('longitude',-180,180)):
                value=float(row[positions[name]])
                if not math.isfinite(value) or not low<=value<=high:
                    raise ValueError(f'Invalid {name} at CSV record {count}.')
            if count>expected_rows:
                raise ValueError('CSV contains more than the expected rows.')
    if count!=expected_rows:
        raise ValueError(f'Expected {expected_rows} CSV records, found {count}.')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return {'rows':count,'couriers':len(couriers),'file_sha256':digest.hexdigest(),
            'file':path.name,'kind':'exported fictional GPS; not a capacity measurement'}


def count_run(client, run_id):
    return int(client.query('SELECT count() AS rows FROM delivery_atlas.courier_positions '
                           'FINAL WHERE simulation_run_id={run:UUID}',{'param_run':run_id})['data'][0]['rows'])


def insert(client, stream, fmt):
    if fmt not in {'CSVWithNames','JSONEachRow'}:
        raise ValueError('Unsupported lab import format.')
    params={'query':'INSERT INTO delivery_atlas.courier_positions FORMAT '+fmt,
            'date_time_input_format':'best_effort','async_insert':0,'wait_end_of_query':1,
            'max_execution_time':300,'max_memory_usage':536870912,'max_threads':2,
            'max_insert_block_size':262144,'min_insert_block_size_rows':262144,
            'min_insert_block_size_bytes':0,'input_format_parallel_parsing':0}
    request=Request(LAB_URL+'?'+urlencode(params),data=stream,
        headers={'X-ClickHouse-User':client.user,'X-ClickHouse-Key':client.password})
    # A timed-out INSERT can have partially succeeded. Never retry it automatically.
    with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=320) as response:
        payload=response.read(4096)
        if payload.strip():
            raise RuntimeError('Unexpected import response: '+payload.decode(errors='replace'))


def fixture_rows(run_id):
    at=datetime(2026,10,31,15,0,tzinfo=timezone.utc)
    namespace=UUID(run_id)
    result=[]
    for courier in range(3):
        # Deliberately out-of-order insertion tests argMax rather than insertion order.
        for step in (2,0,3,1):
            event_time=(at+timedelta(seconds=step)).isoformat(timespec='milliseconds')
            result.append(dict(schema_version=1,event_id=str(uuid5(namespace,f'{courier}:{step}')),
                simulation_run_id=run_id,event_time=event_time,ingested_at=event_time,city_id='madrid',
                courier_id=str(uuid5(namespace,'courier:'+str(courier))),order_id=str(UUID(int=0)),
                latitude=40.4+step*.001,longitude=-3.7+courier*.001,speed_kmh=12,accuracy_m=5,
                source='gps-benchmark-validation-fixture',source_kind='synthetic'))
    return result


def load(client, run_id, source=None, expected_rows=None):
    marker(client)
    if count_run(client,run_id):
        raise ValueError('This run already has lab data. Inspect it; do not reinsert or reset it automatically.')
    if source is not None:
        details=inspect_csv(source,run_id,expected_rows)
        opener=gzip.open if source.suffix=='.gz' else open
        with opener(source,'rb') as stream:
            insert(client,iter(lambda:stream.read(1024*1024),b''),'CSVWithNames')
    else:
        rows=fixture_rows(run_id)
        details={'rows':len(rows),'couriers':3,'kind':'tiny validation fixture; no capacity claim'}
        insert(client,('\n'.join(json.dumps(row) for row in rows)+'\n').encode(),'JSONEachRow')
    if count_run(client,run_id)!=details['rows']:
        raise RuntimeError('Logical row count differs after import. Inspect the lab; no automatic retry.')
    return dict(details,run_id=run_id,loaded_at_utc=datetime.now(timezone.utc).isoformat(),url=LAB_URL)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('fixture',help='Load 12 labelled positions for three couriers.')
    csv_parser=sub.add_parser('load')
    csv_parser.add_argument('--csv',type=Path,required=True)
    csv_parser.add_argument('--run-id',type=lambda s:str(UUID(s)),required=True)
    csv_parser.add_argument('--expected-rows',type=int,required=True)
    args=p.parse_args(argv)
    if args.command=='load' and not 1<=args.expected_rows<=1000000000:
        p.error('Expected rows must be between 1 and 1,000,000,000.')
    run_id=str(uuid4()) if args.command=='fixture' else args.run_id
    result=load(admin_client(),run_id,args.csv if args.command=='load' else None,
                args.expected_rows if args.command=='load' else None)
    out=ROOT/'data/gps-benchmark/loads'
    out.mkdir(parents=True,exist_ok=True)
    path=out/(run_id+'.json')
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    print(f'python scripts/gps_benchmark.py --run-id {run_id} --expected-rows {result["rows"]} '
          f'--expected-couriers {result["couriers"]} --label "Anuar lab: record resources" --smoke')
    return result


if __name__=='__main__':
    main()
