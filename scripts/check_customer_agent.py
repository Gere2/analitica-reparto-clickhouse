"""Real model -> click -> immutable checkout -> delivered order -> stored GPS."""
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from atlas.clickhouse import ClickHouse

def call(path,data=None):
    req=Request('http://127.0.0.1:8001'+path,data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type':'application/json'})
    for attempt in range(3):
        try:
            with urlopen(req,timeout=60) as r:return json.load(r)
        except HTTPError as error:
            if data is not None or error.code!=503 or attempt==2:raise
            time.sleep(2)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['ollama','policy'],default='ollama')
    parser.add_argument('--timeout',type=int,default=360)
    parser.add_argument('--existing',action='store_true',help='Verify the current customer run')
    args=parser.parse_args()
    current=call('/api/simulation')
    if current.get('running') and not args.existing:raise SystemExit('Stop the current run before this check.')
    if args.existing and (current.get('mode')!='customers' or current.get('agent_mode')!=args.mode):raise SystemExit('Current run does not match the requested mode.')
    state=current if args.existing else call('/api/simulation/start',{'mode':'customers','agent_mode':args.mode,'customers':3,'fleet':6,'interval':2,'seed':42})
    run=state['run_id'];print('Started',args.mode,run,flush=True)
    deadline=time.monotonic()+args.timeout;selected=None;stages=set()
    while time.monotonic()<deadline:
        state=call('/api/simulation');data=call('/api/operations');queue=call('/api/status')
        if state.get('agent_state')=='error' or state.get('error') or queue.get('publisher_error'):
            raise RuntimeError('The model/ingestion stopped: '+json.dumps({'state':state,'publisher_error':queue.get('publisher_error')}))
        if not selected and data.get('purchases'):
            selected=data['purchases'][-1];print('Checkout',selected['checkout_event_id'],'-> order',selected['order_id'],flush=True)
        if selected:
            order=next((o for o in data['orders'] if o['order_id']==selected['order_id']),None)
            if order:
                if order['status'] not in stages:
                    stages.add(order['status']);print('Order state:',order['status'],flush=True)
                if order['status']=='delivered':break
        time.sleep(2)
    else:raise RuntimeError('No completed purchase within timeout; check model decisions.')
    ch=ClickHouse();params={'param_run':run,'param_order':selected['order_id'],'param_click':selected['checkout_event_id']}
    link=ch.query('SELECT * FROM delivery_atlas.customer_orders FINAL WHERE simulation_run_id={run:UUID} AND order_id={order:UUID}',params)[0]
    click=ch.query("SELECT toString(event_id) AS event_id,toString(order_id) AS order_id,toString(session_id) AS session_id,source_kind "
        "FROM delivery_atlas.app_events AS e FINAL WHERE e.event_id={click:UUID} AND event_type='order_submitted'",params)
    assert len(click)==1 and click[0]['order_id']==selected['order_id'] and click[0]['session_id']==selected['session_id']
    assert link['amount_minor']==sum(int(i['quantity'])*int(i['unit_price_minor']) for i in link['items'])
    gps=ch.query('SELECT uniqExact(event_id) AS positions,uniqExact(courier_id) AS couriers, min(event_time) AS first,max(event_time) AS last '
        'FROM delivery_atlas.courier_positions WHERE simulation_run_id={run:UUID} AND order_id={order:UUID}',params)[0]
    assert int(gps['positions'])>2 and int(gps['couriers'])==1
    decision_count=ch.query("SELECT uniqExactIf(event_id,decision_mode='ollama') AS n FROM delivery_atlas.customer_activity WHERE simulation_run_id={run:UUID}",params)[0]['n']
    if args.mode=='ollama':assert int(decision_count)>0
    stored_states=ch.query('SELECT status FROM delivery_atlas.order_events FINAL WHERE simulation_run_id={run:UUID} AND order_id={order:UUID} GROUP BY status',params)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'run_id':run,'agent_mode':args.mode,
        'model':state.get('model'),'model_calls':state.get('model_calls'),'published_model_decisions':int(decision_count),
        'order_id':selected['order_id'],'checkout_event_id':selected['checkout_event_id'],
        'session_id':selected['session_id'],'amount_minor':link['amount_minor'],'basket_total_matches':True,
        'checkout_link_verified_in_clickhouse':True,'delivered':True,'observed_states':sorted(stages),'stored_states':sorted(r['status'] for r in stored_states),
        'gps':gps,'scope':'Real local LLM or labelled policy; no payment, no observed customers, no latency SLA.'}
    path=ROOT/'docs/evidencia-clientes.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    print('Run remains active for the dashboard. Stop it with its local control.',flush=True)

if __name__=='__main__':main()
