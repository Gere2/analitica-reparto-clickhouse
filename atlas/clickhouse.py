"""Small standard-library client, fixed database and parameterised filters."""
import base64
import json
import os
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
        return json.loads(self.execute(sql+' FORMAT JSON', params))

    def init(self):
        for name in ('atlas.sql','atlas_operations.sql'):
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
            if stream not in {'app_events','courier_positions','order_events'}:
                raise ValueError('Ruta de publicación desconocida.')
            groups.setdefault(stream,[]).append(json.dumps(event,separators=(',',':'),ensure_ascii=False))
        for stream,payloads in groups.items():
            self.execute('INSERT INTO delivery_atlas.'+stream+' FORMAT JSONEachRow\n'+'\n'.join(payloads))

    def operations(self, run_id):
        params={'param_run':run_id}
        couriers=self.query("SELECT toString(courier_id) AS courier_id,toString(order_id) AS order_id,"
            "city_id,latitude,longitude,speed_kmh,accuracy_m,toString(event_time) AS event_time,"
            "toString(ingested_at) AS ingested_at,dateDiff('millisecond',p.event_time,now64(3)) AS age_ms,"
            "dateDiff('millisecond',p.event_time,p.ingested_at) AS receipt_delay_ms "
            "FROM delivery_atlas.courier_latest AS p WHERE simulation_run_id={run:UUID} ORDER BY courier_id LIMIT 100",params)
        orders=self.query("SELECT toString(order_id) AS order_id,toString(courier_id) AS courier_id,"
            "city_id,restaurant_id,status,amount_minor,currency,pickup_lat,pickup_lon,dropoff_lat,dropoff_lon,"
            "toString(order_created_at) AS order_created_at,toString(promised_delivery_at) AS promised_delivery_at,"
            "toString(event_time) AS event_time FROM delivery_atlas.order_latest "
            "WHERE simulation_run_id={run:UUID} ORDER BY event_time DESC LIMIT 200",params)
        metrics=self.query("SELECT count() AS orders,countIf(status='delivered') AS delivered,"
            "countIf(status='cancelled') AS cancelled,countIf(status NOT IN ('delivered','cancelled')) AS active,"
            "sumIf(amount_minor,status='delivered') AS delivered_amount_minor,"
            "countIf(status NOT IN ('delivered','cancelled') AND promised_delivery_at<now64(3)) AS late "
            "FROM delivery_atlas.order_latest WHERE simulation_run_id={run:UUID}",params)[0]
        rate=self.query("SELECT toString(toStartOfInterval(event_time,INTERVAL 5 SECOND)) AS bucket,"
            "uniqExact(event_id) AS positions FROM delivery_atlas.courier_positions "
            "WHERE simulation_run_id={run:UUID} AND event_time>=now()-INTERVAL 2 MINUTE "
            "GROUP BY bucket ORDER BY bucket",params)
        return {'couriers':couriers,'orders':orders,'metrics':metrics,'positions_by_5s':rate,
                'source_kind':'synthetic','run_id':run_id,'truncated':len(orders)==200,
                'snapshot_at':self.query('SELECT toString(now64(3)) AS at')[0]['at']}

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
