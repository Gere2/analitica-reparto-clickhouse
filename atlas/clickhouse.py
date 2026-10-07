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
                    'wait_end_of_query': '1', **(params or {})}
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
        sql = (Path(__file__).resolve().parents[1]/'sql/atlas.sql').read_text()
        sql = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
        for statement in sql.split(';'):
            if statement.strip():
                self.execute(statement)

    def publish(self, rows):
        self.execute('INSERT INTO delivery_atlas.app_events FORMAT JSONEachRow\n'+'\n'.join(rows))

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
        total = self.query('SELECT sum(events) AS events, count() AS groups FROM delivery_atlas.app_daily_counts'+where, params)[0]
        return {'events': int(total['events']), 'groups': int(total['groups']), 'rows': rows,
                'truncated': int(total['groups']) > 10000,
                'meaning': 'Eventos lógicos. Simulación y acciones manuales conservan su procedencia.'}
