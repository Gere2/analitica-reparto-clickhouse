"""Small standard-library client, fixed database and parameterised filters."""
import base64
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class ClickHouse:
    def __init__(self):
        self.url = os.environ.get('CLICKHOUSE_URL', 'http://127.0.0.1:8124/').rstrip('/')
        self.auth = base64.b64encode((os.environ.get('CLICKHOUSE_USER','demo')+':'+os.environ.get('CLICKHOUSE_PASSWORD','demo')).encode()).decode()

    def execute(self, sql, params=None):
        settings = {'date_time_input_format': 'best_effort', 'async_insert': '0',
                    'wait_end_of_query': '1', 'max_threads':'4', **(params or {})}
        request = Request(self.url+'/?'+urlencode(settings), data=sql.encode(),
                          headers={'Authorization': 'Basic '+self.auth})
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as error:
            raise OSError('ClickHouse: '+error.read().decode(errors='replace')[:1600]) from error

    def query(self, sql, params=None):
        return self.result(sql, params)['data']

    def result(self, sql, params=None):
        # Background merges can briefly exhaust the classroom node's global
        # memory budget. Retry reads only; never replay a write here.
        for attempt in range(3):
            try:
                return json.loads(self.execute(sql+' FORMAT JSON', params))
            except OSError as error:
                if 'Code: 241' not in str(error) or attempt==2:raise
                time.sleep(.25*(attempt+1))

    def init(self):
        for name in ('atlas.sql','atlas_operations.sql','atlas_agents.sql','atlas_miniapp.sql'):
            sql = (Path(__file__).resolve().parents[1]/'sql'/name).read_text()
            sql = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
            for statement in sql.split(';'):
                if statement.strip():
                    self.execute(statement)

    def publish(self, rows):
        groups={}
        for raw in rows:
            event=json.loads(raw)
            stream=event.pop('_stream','app_events')
            if stream not in {'app_events','courier_positions','order_events','customer_activity','customer_orders'}:
                raise ValueError('Ruta de publicación desconocida.')
            if stream=='customer_orders':
                # JSONEachRow parses named Tuples as objects. Transform at the boundary,
                # preserving the immutable queued payload and retry digest.
                event['items']=[dict(zip(('product_id','quantity','unit_price_minor'),item))
                    if isinstance(item,list) and len(item)==3 else item for item in event['items']]
            groups.setdefault(stream,[]).append(json.dumps(event,separators=(',',':'),ensure_ascii=False))
        for stream,payloads in groups.items():
            self.execute('INSERT INTO delivery_atlas.'+stream+' FORMAT JSONEachRow\n'+'\n'.join(payloads))

    def operations(self, run_id):
        params={'param_run':run_id}
        couriers=self.query("SELECT toString(courier_id) AS courier_id,toString(order_id) AS order_id,"
            "city_id,latitude,longitude,speed_kmh,accuracy_m,toString(event_time) AS event_time,"
            "toString(ingested_at) AS ingested_at,dateDiff('millisecond',p.event_time,now64(3)) AS age_ms,"
            "dateDiff('millisecond',p.event_time,p.ingested_at) AS receipt_delay_ms "
            "FROM delivery_atlas.courier_latest AS p WHERE simulation_run_id={run:UUID} ORDER BY courier_id LIMIT 150",params)
        orders=self.query("SELECT toString(order_id) AS order_id,toString(courier_id) AS courier_id,"
            "city_id,restaurant_id,status,amount_minor,currency,pickup_lat,pickup_lon,dropoff_lat,dropoff_lon,"
            "toString(order_created_at) AS order_created_at,toString(promised_delivery_at) AS promised_delivery_at,"
            "toString(event_time) AS event_time FROM delivery_atlas.order_latest AS o "
            "WHERE simulation_run_id={run:UUID} ORDER BY (o.status IN ('delivered','cancelled')), "
            "(o.courier_id=toUUID('00000000-0000-0000-0000-000000000000')),o.event_time DESC LIMIT 200",params)
        metrics=self.query("SELECT count() AS orders,countIf(status='delivered') AS delivered,"
            "countIf(status='cancelled') AS cancelled,countIf(status NOT IN ('delivered','cancelled')) AS active,"
            "sumIf(amount_minor,status='delivered') AS delivered_amount_minor,"
            "countIf(status NOT IN ('delivered','cancelled') AND promised_delivery_at<now64(3)) AS late "
            "FROM delivery_atlas.order_latest WHERE simulation_run_id={run:UUID}",params)[0]
        rate=self.query("SELECT toString(toStartOfInterval(event_time,INTERVAL 5 SECOND)) AS bucket,"
            "uniqExact(event_id) AS positions FROM delivery_atlas.courier_positions "
            "WHERE simulation_run_id={run:UUID} AND event_time>=now()-INTERVAL 2 MINUTE "
            "GROUP BY bucket ORDER BY bucket",params)
        customer_data=self.customers(run_id)
        links={r['order_id']:r for r in customer_data['purchases']}
        missing=[r['order_id'] for r in orders if r['order_id'] not in links]
        if missing:
            # Recent purchases and current orders are different windows once
            # hundreds of clients buy. Resolve every displayed order's link.
            link_params={**params,'param_ids':'['+','.join("'"+i+"'" for i in missing)+']'}
            older=self.query("SELECT toString(order_id) AS order_id,toString(customer_id) AS customer_id,"
                "toString(session_id) AS session_id,toString(checkout_event_id) AS checkout_event_id,items,decision_mode "
                "FROM delivery_atlas.customer_orders AS p FINAL WHERE simulation_run_id={run:UUID} AND p.order_id IN {ids:Array(UUID)}",link_params)
            links.update({r['order_id']:r for r in older})
        for row in orders:
            if row['order_id'] in links:
                row.update({k:v for k,v in links[row['order_id']].items() if k not in {'event_time','amount_minor'}})
        return {'couriers':couriers,'orders':orders,'metrics':metrics,'positions_by_5s':rate,
                **customer_data,
                'source_kind':'synthetic','run_id':run_id,'truncated':len(orders)==200,
                'snapshot_at':self.query('SELECT toString(now64(3)) AS at')[0]['at']}

    def customers(self,run_id):
        params={'param_run':run_id}
        if not hasattr(self,'_demo_labels'):
            self._demo_labels={
                'products':{r['product_id']:r['product_name'] for r in self.query('SELECT product_id,product_name FROM delivery_atlas.demo_products FINAL')},
                'restaurants':{r['restaurant_id']:r['name'] for r in self.query('SELECT restaurant_id,name FROM delivery_atlas.demo_restaurants FINAL')}}
        customers=self.query("SELECT toString(customer_id) AS customer_id,toString(session_id) AS session_id,"
            "toString(event_time) AS event_time,customer_label,objective,budget_minor,action,stage,reason,"
            "restaurant_id,product_id,toString(order_id) AS order_id,cart_total_minor,decision_mode,model "
            "FROM delivery_atlas.customer_latest WHERE simulation_run_id={run:UUID} ORDER BY customer_label",params)
        activity=self.query("SELECT toString(event_id) AS event_id,customer_label,toString(customer_id) AS customer_id,"
            "toString(session_id) AS session_id,toString(event_time) AS event_time,action,reason,"
            "decision_mode,model,toString(order_id) AS order_id,restaurant_id,product_id "
            "FROM delivery_atlas.customer_activity FINAL WHERE simulation_run_id={run:UUID} "
            "ORDER BY event_time DESC,event_id DESC LIMIT 30",params)
        for row in customers+activity:
            row['product_name']=self._demo_labels['products'].get(row.get('product_id'))
            row['restaurant_name']=self._demo_labels['restaurants'].get(row.get('restaurant_id'))
        purchases=self.query("SELECT toString(order_id) AS order_id,toString(customer_id) AS customer_id,"
            "toString(session_id) AS session_id,toString(checkout_event_id) AS checkout_event_id,"
            "restaurant_id,items,amount_minor,decision_mode,toString(event_time) AS event_time "
            "FROM delivery_atlas.customer_orders FINAL WHERE simulation_run_id={run:UUID} ORDER BY event_time DESC LIMIT 200",params)
        flow=self.query("SELECT uniqExact(session_id) AS sessions,"
            "uniqExactIf(session_id,action='checkout') AS purchasing_sessions,"
            "uniqExactIf(session_id,action='abandon') AS abandoned_sessions,"
            "uniqExactIf(event_id,decision_mode='ollama') AS model_decisions,"
            "uniqExactIf(event_id,action IN ('search','open_restaurant','open_product','add_to_cart','remove_from_cart','checkout','abandon')) AS clicks,"
            "uniqExactIf(event_id,action='checkout') AS checkouts "
            "FROM delivery_atlas.customer_activity WHERE simulation_run_id={run:UUID}",params)[0]
        return {'customers':customers,'activity':activity,'purchases':purchases,'customer_metrics':flow}

    def history(self,run_id,courier_id):
        return self.query("SELECT latitude,longitude,toString(order_id) AS order_id,toString(event_time) AS event_time FROM "
            "delivery_atlas.courier_positions FINAL WHERE simulation_run_id={run:UUID} "
            "AND courier_id={courier:UUID} ORDER BY event_time DESC,event_id DESC LIMIT 240",
            {'param_run':run_id,'param_courier':courier_id})[::-1]

    def summary(self, filters):
        clauses, params = [], {}
        for name, type_ in [('city_id','String'), ('source_kind','String'), ('event_type','String')]:
            if name in filters:
                clauses.append(f'{name} = {{f_{name}:{type_}}}')
                params['param_f_'+name] = filters[name]
        for name, op in [('from','>='), ('to','<=')]:
            if name in filters:
                clauses.append(f'event_date {op} {{f_{name}:Date}}')
                params['param_f_'+name] = filters[name]
        where = ' WHERE '+' AND '.join(clauses) if clauses else ''
        rows = self.query('SELECT toString(event_date) AS day, city_id, section, event_type, '
                          'toString(source_kind) AS source_kind, events FROM delivery_atlas.app_daily_counts'
                          +where+' ORDER BY day,city_id,event_type LIMIT 10000', params)
        if len(rows)<10000:
            total={'events':sum(int(row['events']) for row in rows),'groups':len(rows)}
        else:
            total = self.query('SELECT sum(events) AS events, count() AS groups FROM delivery_atlas.app_daily_counts'+where, params)[0]
        return {'events': int(total['events']), 'groups': int(total['groups']), 'rows': rows,
                'truncated': int(total['groups']) > 10000,
                'meaning': 'Eventos lógicos. Simulación y acciones manuales conservan su procedencia.'}
