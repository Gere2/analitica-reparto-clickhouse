"""Fixed analytical reads for the classroom portal. No client-supplied SQL."""
from datetime import date
from uuid import UUID
import time


DATASETS = {'otto', 'rees46', 'eleme', 'glovo', 'criteo'}
MONTHS = {'ALL', '201910', '201911', '201912', '202001', '202002', '202003', '202004'}
ROUTES = {'journey', 'performance', 'benchmark', 'historical'}


def validate_filters(endpoint, values):
    allowed = {'journey': {'run_id', 'kind'}, 'performance': set(),
               'benchmark': {'workload'}, 'historical': {'dataset', 'period', 'country', 'city'}}[endpoint]
    if set(values) - allowed or any(len(v) != 1 or not v[0] for v in values.values()):
        raise ValueError('Unknown, empty or repeated analytical filter.')
    filters = {k: v[0] for k, v in values.items()}
    if endpoint == 'journey':
        if 'run_id' in filters:
            filters['run_id'] = str(UUID(filters['run_id']))
        filters.setdefault('kind', 'all')
        if filters['kind'] not in {'all', 'ai', 'simulated'}:
            raise ValueError('Choose all, ai or simulated customers.')
    if endpoint == 'benchmark':
        filters.setdefault('workload', 'atlas')
        if filters['workload'] not in {'atlas', 'otto'}:
            raise ValueError('Choose the Atlas or OTTO comparison.')
    if endpoint == 'historical':
        dataset = filters.setdefault('dataset', 'otto')
        if dataset not in DATASETS:
            raise ValueError('Dataset not available.')
        if set(filters) - ({'dataset', 'period'} if dataset in {'rees46', 'eleme'} else
                           {'dataset', 'country', 'city'} if dataset == 'glovo' else {'dataset'}):
            raise ValueError('This filter does not apply to the selected dataset.')
        if dataset in {'rees46', 'eleme'}:
            filters.setdefault('period', 'ALL')
            if filters['period'] not in (MONTHS if dataset == 'rees46' else {'ALL', *map(str, range(1, 9))}):
                raise ValueError('Period not available.')
        if dataset == 'glovo':
            import re
            filters.setdefault('country', 'ES')
            if filters['country'] != 'ALL' and not re.fullmatch('[A-Z]{2}', filters['country']):
                raise ValueError('Invalid country code.')
            if 'city' in filters and (filters['country'] == 'ALL' or not re.fullmatch('[A-Z0-9_-]{2,10}', filters['city'])):
                raise ValueError('Choose a country and a valid city code.')
    return filters


class Analytics:
    def __init__(self, ch):
        self.ch = ch
        self.queries = []
        self.started = time.monotonic()

    def read(self, label, sql, params=None):
        remaining = 20 - (time.monotonic() - self.started)
        if remaining <= 0:
            raise OSError('Analytical snapshot exceeded its time budget.')
        result = self.ch.result(sql, {'max_execution_time': str(min(8, remaining)), 'max_memory_usage': '268435456',
                                      'use_query_cache': '0', **(params or {})})
        stats = result.get('statistics', {})
        self.queries.append({'label': label, 'sql': sql, 'elapsed_ms': round(float(stats.get('elapsed', 0)) * 1000, 3),
                             'rows_read': int(stats.get('rows_read', 0)), 'bytes_read': int(stats.get('bytes_read', 0))})
        return result['data']

    def exists(self, table):
        return bool(self.ch.query('EXISTS TABLE ' + table)[0]['result'])

    def finish(self, **data):
        return dict(data, queries=self.queries,
                    queried_at=self.ch.query('SELECT toString(now64(3)) AS at')[0]['at'])

    def journey(self, run_id, kind='all'):
        if not run_id:
            return self.finish(run_id=None, kind=kind, available=False,
                               message='Start a customer simulation on the host to analyse a run.')
        params = {'param_run': run_id}
        where = 'simulation_run_id={run:UUID}'
        if kind != 'all':
            where += (" AND customer_id IN (SELECT customer_id FROM delivery_atlas.customer_activity "
                      "WHERE simulation_run_id={run:UUID} GROUP BY customer_id "
                      "HAVING max(decision_mode='ollama')=" + ('1' if kind == 'ai' else '0') + ')')
        # Strictly increasing event times make the ordering contract explicit.
        # Repeated events are removed by FINAL before the per-session funnel.
        levels = self.read('Ordered sessions with windowFunnel',
            "SELECT level,count() AS sessions,countIf(abandoned) AS abandoned_sessions FROM ("
            "SELECT session_id,windowFunnel(1800000,'strict_increase')(toUInt64(toUnixTimestamp64Milli(event_time)),"
            "action='session_started',action='open_product',action='add_to_cart',action='checkout') AS level,"
            "max(action='abandon') AS abandoned FROM delivery_atlas.customer_activity FINAL WHERE " + where +
            ' GROUP BY session_id) GROUP BY level ORDER BY level', params)
        counts = [sum(int(r['sessions']) for r in levels if int(r['level']) >= i) for i in range(1, 5)]
        cohort = counts[0]
        steps = [{'label': label, 'sessions': count, 'share_pct': round(count / cohort * 100, 2) if cohort else None}
                 for label, count in zip(['Session started', 'Product opened', 'Cart added', 'Checkout'], counts)]
        actions = self.read('Logical actions by type',
            'SELECT action,count() AS events,uniqExact(session_id) AS sessions '
            'FROM delivery_atlas.customer_activity FINAL WHERE ' + where + ' GROUP BY action ORDER BY events DESC,action', params)
        timeline = self.read('Minute-level session activity',
            "SELECT toString(toStartOfMinute(event_time)) AS bucket,uniqExact(session_id) AS active_sessions,"
            "uniqExactIf(session_id,action='checkout') AS checkout_sessions,"
            "uniqExactIf(session_id,action='abandon') AS abandoned_sessions "
            'FROM delivery_atlas.customer_activity FINAL WHERE ' + where +
            ' GROUP BY bucket ORDER BY bucket DESC LIMIT 60', params)[::-1]
        return self.finish(available=True, run_id=run_id, kind=kind, steps=steps, actions=actions, timeline=timeline,
            cohort_sessions=cohort, excluded_sessions=sum(int(r['sessions']) for r in levels if int(r['level']) == 0),
            abandoned_sessions=sum(int(r['abandoned_sessions']) for r in levels if int(r['level']) > 0),
            definition='One run, unique sessions, ordered steps within 30 minutes. Equal timestamps do not advance twice. '
                       'An unfinished step is not an observed abandonment. Uses customer_activity, not manual miniapp browsing. '
                       'Charts use separate queries, so continued ingestion can advance totals between reads.',
            classification='AI means the customer has a recorded model decision in this run. Waiting AI customers may still count as simulated.')

    def performance(self):
        server = self.ch.query('SELECT version() AS version')[0]
        tables = self.read('Physical storage and sorting keys',
            "SELECT p.database,p.table,any(t.engine) AS engine,any(t.sorting_key) AS sorting_key,"
            "any(t.partition_key) AS partition_key,count() AS active_parts,sum(p.rows) AS physical_rows,"
            "sum(p.bytes_on_disk) AS disk_bytes,sum(p.data_compressed_bytes) AS compressed_bytes,"
            "sum(p.data_uncompressed_bytes) AS uncompressed_bytes FROM system.parts AS p "
            "LEFT JOIN system.tables AS t ON p.database=t.database AND p.table=t.name "
            "WHERE p.active AND p.database IN ('delivery','delivery_atlas') "
            'GROUP BY p.database,p.table ORDER BY physical_rows DESC,p.database,p.table LIMIT 60')
        log_available = True
        try:
            history = self.read('Completed analytical query families in the last hour',
                "SELECT toString(normalized_query_hash) AS query_family,arrayStringConcat(tables,', ') AS source_tables,"
                "count() AS executions,round(quantileExact(0.5)(query_duration_ms),2) AS median_ms,"
                "max(query_duration_ms) AS slowest_ms,max(memory_usage) AS peak_memory_bytes,"
                "round(avg(read_rows)) AS average_rows_read FROM system.query_log "
                "WHERE type='QueryFinish' AND is_initial_query=1 AND query_kind='Select' "
                "AND event_time>=now()-INTERVAL 1 HOUR "
                "AND arrayExists(db->db IN ('delivery','delivery_atlas'),databases) "
                'GROUP BY query_family,source_tables ORDER BY max(event_time) DESC LIMIT 12')
        except OSError:
            history, log_available = [], False
        return self.finish(version=server['version'], tables=tables, history=history, log_available=log_available,
            definition='Active parts report physical rows, not unique events. Compression compares column bytes before and after compression. '
                       'Query logs flush asynchronously. Timings are server-side and exclude browser and gateway latency.')

    def benchmark(self, workload):
        params = {}
        if workload == 'otto':
            source, aggregate = 'delivery.otto_archive', 'delivery.otto_daily_rollup'
            if not self.exists(source) or not self.exists(aggregate):
                return self.finish(available=False, workload=workload, message='Load the OTTO archive and its daily aggregate on this host first.')
            detail = 'SELECT toDate(event_time) AS event_date,event_type,count() AS events FROM delivery.otto_archive GROUP BY event_date,event_type ORDER BY event_date,event_type'
            rollup = 'SELECT event_date,event_type,sum(events) AS events FROM delivery.otto_daily_rollup GROUP BY event_date,event_type ORDER BY event_date,event_type'
            scope = 'All loaded OTTO dates. Same daily counts by event type.'
        else:
            source, aggregate = 'delivery_atlas.app_events', 'delivery_atlas.app_daily_counts'
            if not self.exists(aggregate):
                return self.finish(available=False, workload=workload, message='Initialise the Atlas schema on this host first.')
            rows = self.ch.query("SELECT toString(maxOrNull(event_date)) AS day FROM delivery_atlas.app_daily_rollup "
                                 "WHERE source_kind='synthetic' AND city_id='madrid'")
            if not rows[0]['day']:
                return self.finish(available=False, workload=workload, message='No synthetic Madrid app events have reached the aggregate yet.')
            day = date.fromisoformat(rows[0]['day'])
            params = {'param_day': day.isoformat()}
            where = "source_kind='synthetic' AND city_id='madrid' AND event_date={day:Date}"
            detail = 'SELECT section,event_type,uniqExact(event_id) AS events FROM delivery_atlas.app_events FINAL WHERE ' + where + ' GROUP BY section,event_type ORDER BY section,event_type'
            rollup = 'SELECT section,event_type,sum(events) AS events FROM delivery_atlas.app_daily_counts WHERE ' + where + ' GROUP BY section,event_type ORDER BY section,event_type'
            scope = f'Synthetic Madrid app events on {day}. All runs on that date, because this aggregate has no run dimension.'
        before = self.read('Detail query', detail, params)
        after = self.read('Prepared aggregate query', rollup, params)
        normalize = lambda rows: [dict(r, events=int(r['events'])) for r in rows]
        same = normalize(before) == normalize(after)
        a, b = self.queries
        return self.finish(available=True, workload=workload, scope=scope, same_result=same,
            detail=a, aggregate=b, result_groups=len(before), logical_events=sum(int(r['events']) for r in before),
            ratio=a['elapsed_ms']/b['elapsed_ms'] if same and b['elapsed_ms'] > 0 else None,
            definition='One live read per design, detail first, SQL query cache disabled, bounded to 8 seconds and 256 MiB per query. '
                       'System cache, query order and concurrent ingestion can affect the result. This is not a controlled benchmark or a comparison with another database.')

    def historical(self, dataset, **filters):
        table = {'otto': 'otto_archive', 'rees46': 'rees46_events', 'eleme': 'eleme_samples',
                 'glovo': 'glovo_products', 'criteo': 'criteo_uplift'}[dataset]
        if not self.exists('delivery.' + table):
            return self.finish(available=False, dataset=dataset, table='delivery.' + table,
                               message='This dataset is not loaded on this host. The Atlas simulation and map work independently.')
        params, charts = {}, []
        if dataset == 'otto':
            meaning = 'Historical ecommerce events. Article IDs are anonymous. Event counts are not a session conversion funnel.'
            metrics = self.read('Archive coverage', 'SELECT count() AS events,uniqCombined64(session_id) AS sessions_approx FROM delivery.otto_archive')[0]
            charts.append(self.chart('Events by day and action', 'Date', self.read('Daily event counts',
                'SELECT toString(toDate(event_time)) AS label,event_type AS series,count() AS value FROM delivery.otto_archive GROUP BY label,series ORDER BY label,series')))
            charts.append(self.chart('Actions in the archive', 'Action', self.read('Event types',
                'SELECT event_type AS label,count() AS value FROM delivery.otto_archive GROUP BY label ORDER BY value DESC')))
            charts.append(self.chart('Most active article IDs', 'Article ID', self.read('Top articles',
                'SELECT toString(article_id) AS label,count() AS value FROM delivery.otto_archive GROUP BY label ORDER BY value DESC,label LIMIT 10')))
        elif dataset == 'rees46':
            period = filters.get('period', 'ALL')
            where = '1' if period == 'ALL' else 'toYYYYMM(event_date)={period:UInt32}'
            params = {} if period == 'ALL' else {'param_period': period}
            meaning = 'Historical product views, carts and purchases. Populations are separate from OTTO and our fictional platform.'
            metrics = self.read('Selected marketplace events', 'SELECT count() AS events,uniqCombined64(user_id) AS users_approx FROM delivery.rees46_events WHERE ' + where, params)[0]
            charts.append(self.chart('Activity by month and action', 'Month', self.read('Monthly event counts',
                'SELECT toString(toYYYYMM(event_date)) AS label,event_type AS series,count() AS value FROM delivery.rees46_events WHERE ' + where + ' GROUP BY label,series ORDER BY label,series', params)))
            charts.append(self.chart('Categories by product views', 'Category', self.read('Viewed categories',
                "SELECT category_code AS label,countIf(event_type='view') AS value FROM delivery.rees46_events WHERE " + where + " AND category_code!='' GROUP BY label ORDER BY value DESC,label LIMIT 10", params)))
            charts.append(self.chart('Brand activity', 'Brand', self.read('Brand counts',
                "SELECT brand AS label,count() AS value FROM delivery.rees46_events WHERE " + where + " AND brand!='' GROUP BY label ORDER BY value DESC,label LIMIT 10", params)))
        elif dataset == 'eleme':
            period = filters.get('period', 'ALL')
            where = '1' if period == 'ALL' else 'sample_day={period:UInt8}'
            params = {} if period == 'ALL' else {'param_period': period}
            meaning = 'Recommendation samples from China. Positive labels describe the loaded sample, not whole-app CTR. Days and cities use the source identifiers.'
            metrics = self.read('Recommendation sample coverage', 'SELECT count() AS samples,sum(clicked) AS positive_labels,uniqCombined64(user_id) AS users_approx FROM delivery.eleme_samples WHERE ' + where, params)[0]
            for title, column in [('Samples by relative day', 'sample_day'), ('Samples by hour', 'request_hour'), ('Positive labels by meal period', 'meal_period')]:
                value = 'sum(clicked)' if column == 'meal_period' else 'count()'
                charts.append(self.chart(title, column.replace('_', ' ').title(), self.read(title,
                    f'SELECT toString({column}) AS label,{value} AS value FROM delivery.eleme_samples WHERE ' + where + f' GROUP BY {column} ORDER BY {column}', params)))
        elif dataset == 'glovo':
            where = '1'
            if filters.get('country', 'ES') != 'ALL':
                where += ' AND country_code={country:String}'
                params['param_country'] = filters.get('country', 'ES')
            if filters.get('city'):
                where += ' AND city_code={city:String}'
                params['param_city'] = filters['city']
            meaning = 'A published product catalog. Catalog size describes supply, not demand, orders, revenue or courier locations.'
            metrics = self.read('Selected catalog coverage', 'SELECT count() AS products,uniqExact(store_name) AS store_names,uniqExact((country_code,city_code)) AS cities FROM delivery.glovo_products WHERE ' + where, params)[0]
            for title, column in [('Catalog entries by city', "concat(country_code,'/',city_code)"), ('Catalog sections', 'collection_section'), ('Stores by catalog size', 'store_name')]:
                charts.append(self.chart(title, 'Catalog group', self.read(title,
                    f'SELECT {column} AS label,count() AS value FROM delivery.glovo_products WHERE ' + where + " AND " + column + "!='' GROUP BY label ORDER BY value DESC,label LIMIT 12", params)))
        else:
            meaning = 'Released advertising user records. Non-uniform privacy sampling prevents recovery of the original campaign incrementality. These are observed group summaries.'
            metrics = self.read('Advertising data coverage', 'SELECT count() AS users,sum(visit) AS visits,sum(conversion) AS purchases FROM delivery.criteo_uplift')[0]
            rows = self.read('Observed outcomes by released group',
                "SELECT if(treatment=1,'Treatment','Control') AS label,count() AS users,avg(visit)*100 AS visit_pct,avg(conversion)*100 AS purchase_pct FROM delivery.criteo_uplift GROUP BY treatment ORDER BY treatment")
            for title, field in [('Users per released group', 'users'), ('Observed visits (%)', 'visit_pct'), ('Observed purchases (%)', 'purchase_pct')]:
                charts.append(self.chart(title, 'Group', [{'label': r['label'], 'value': r[field]} for r in rows]))
        return self.finish(available=True, dataset=dataset, table='delivery.' + table, metrics=metrics, charts=charts, meaning=meaning)

    @staticmethod
    def chart(title, label, rows):
        return {'title': title, 'label': label, 'rows': rows}
