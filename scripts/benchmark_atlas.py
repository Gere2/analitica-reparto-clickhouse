"""Compare identical logical counts in the new Atlas database, not the old OTTO table."""
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atlas.clickhouse import ClickHouse
from scripts.atlas import call

def main():
    if call('http://127.0.0.1:8001','/api/status')['pending']:
        raise SystemExit('Esperar a pending=0 y detener generadores antes del benchmark.')
    ch=ClickHouse()
    queries={
      'detail':'SELECT event_date,city_id,section,event_type,source_kind,count() AS events '
               'FROM delivery_atlas.app_events FINAL GROUP BY event_date,city_id,section,event_type,source_kind '
               'ORDER BY event_date,city_id,section,event_type,source_kind',
      'rollup':'SELECT event_date,city_id,section,event_type,source_kind,events '
               'FROM delivery_atlas.app_daily_counts ORDER BY event_date,city_id,section,event_type,source_kind'
    }
    expected=None; output={}
    for name,sql in queries.items():
        runs=[]
        for _ in range(3):
            tick=time.monotonic();result=ch.result(sql,{'use_query_cache':'0'})
            elapsed=time.monotonic()-tick
            if expected is None:
                expected=result['data']
            assert result['data']==expected, 'Resultados diferentes: parar comparación'
            runs.append({'wall_seconds':elapsed,**result['statistics']})
        output[name]={'median_wall_seconds':statistics.median(r['wall_seconds'] for r in runs),'runs':runs}
    output.update({'checked_at':datetime.now(timezone.utc).isoformat(),
                   'logical_events':sum(int(r['events']) for r in expected),'groups':len(expected),
                   'same_result':True,'version':ch.query('SELECT version() AS version')[0]['version'],
                   'query_cache':False,'scope':'Tres consultas por alternativa en el nodo local. No compara motores ni capacidad de producción.',
                   'queries':queries})
    out=ROOT/'data/atlas';out.mkdir(parents=True,exist_ok=True)
    (out/'benchmark.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
