"""Meaningful SQL checks: ordered sessions, retries, scopes and equal answers."""
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from atlas.analytics import Analytics, validate_filters
from atlas.clickhouse import ClickHouse
from atlas.share import canonical_path


class AnalyticalFiltersTests(unittest.TestCase):
    def test_public_routes_reject_sql_names_and_invalid_scopes(self):
        for path in ('/api/journey?kind=real', '/api/journey?run_id=no',
                     '/api/journey?kind=ai&kind=all', '/api/performance?sql=SELECT+1',
                     '/api/benchmark?workload=system.users', '/api/historical?dataset=system',
                     '/api/historical?dataset=otto&period=ALL',
                     '/api/historical?dataset=rees46&period=202610',
                     '/api/historical?dataset=glovo&country=ALL&city=MAD',
                     '/api/historical?dataset=glovo&country=ES&city=SQL%27'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                canonical_path(path)

    def test_validated_defaults_match_the_canonical_shared_request(self):
        self.assertEqual(canonical_path('/api/journey'), ('journey', '/api/journey?kind=all'))
        self.assertEqual(canonical_path('/api/benchmark'), ('benchmark', '/api/benchmark?workload=atlas'))
        self.assertEqual(validate_filters('historical', {'dataset': ['glovo']}), {'dataset': 'glovo', 'country': 'ES'})


@unittest.skipUnless(os.environ.get('ATLAS_TEST_CLICKHOUSE_URL'), 'Requires a disposable ClickHouse instance')
class AnalyticsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ch = ClickHouse()
        cls.ch.url = os.environ['ATLAS_TEST_CLICKHOUSE_URL'].rstrip('/')
        cls.raw = cls.ch.execute
        cls.atlas_db, cls.history_db = 'test_analytics_' + uuid4().hex, 'test_history_' + uuid4().hex
        cls.raw('CREATE DATABASE ' + cls.history_db)

        def isolated(sql, params=None):
            return cls.raw(sql.replace('delivery_atlas', cls.atlas_db).replace('delivery.', cls.history_db + '.')
                           .replace("'delivery'", "'" + cls.history_db + "'"), params)
        cls.ch.execute = isolated
        cls.ch.init()
        schema = (Path(__file__).resolve().parents[1] / 'sql/schema.sql').read_text()
        for name in ('otto_archive', 'otto_daily_rollup', 'otto_daily_rollup_mv', 'rees46_events'):
            marker = ('CREATE MATERIALIZED VIEW IF NOT EXISTS delivery.' if name.endswith('_mv') else
                      'CREATE TABLE IF NOT EXISTS delivery.') + name
            cls.ch.execute(marker + schema.split(marker, 1)[1].split(';', 1)[0])
        cls.ch.execute("INSERT INTO delivery.otto_archive VALUES (1,10,'2022-08-01 10:00:00','clicks',0),"
                       "(1,10,'2022-08-01 10:01:00','carts',1),(2,20,'2022-08-02 10:00:00','clicks',0)")
        cls.ch.execute("INSERT INTO delivery.rees46_events (event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session) "
                       "VALUES ('2019-10-01 10:00:00','view',1,2,'food','demo',1,3,'s1'),"
                       "('2019-11-01 10:00:00','purchase',1,2,'food','demo',1,3,'s2')")
        cls.ch.execute('CREATE TABLE delivery.glovo_products (source_row UInt64,country_code String,city_code String,'
                       'store_name String,collection_section String) ENGINE=MergeTree ORDER BY source_row')
        cls.ch.execute("INSERT INTO delivery.glovo_products VALUES (1,'ES','MAD','Shop','Meals'),(2,'ES','BCN','Other','Drinks'),(3,'FR','PAR','Paris','Meals')")
        cls.ch.execute((Path(__file__).resolve().parents[1] / 'sql/eleme.sql').read_text().split('CREATE TABLE IF NOT EXISTS delivery.eleme_staging')[0].replace('CREATE DATABASE IF NOT EXISTS delivery;', ''))
        cls.ch.execute("INSERT INTO delivery.eleme_samples (source_id,source_file,source_row,sample_day,clicked,user_id,shop_id,item_id,city_id,district_id,category_id,request_hour,weekday,meal_period,request_time_raw,raw_features) "
                       "VALUES ('" + '0' * 64 + "','fixture',1,1,1,'u','s','i','1','d','c',12,'1','lunch','','')")
        schema = (Path(__file__).resolve().parents[1] / 'sql/criteo.sql').read_text()
        for statement in schema.split(';'):
            if 'CREATE TABLE' in statement:
                cls.ch.execute(statement)
        cls.ch.execute('INSERT INTO delivery.criteo_uplift VALUES (' + ','.join(['0'] * 12) + ',0,0,1,0),('
                       + ','.join(['0'] * 12) + ',1,1,1,1)')

    @classmethod
    def tearDownClass(cls):
        cls.raw('DROP DATABASE IF EXISTS ' + cls.atlas_db)
        cls.raw('DROP DATABASE IF EXISTS ' + cls.history_db)

    def activity(self, run, customer, session, action, at, model=False):
        return dict(schema_version=1, event_id=str(uuid4()), simulation_run_id=run,
                    customer_id=customer, session_id=session, event_time=at.isoformat(), ingested_at=at.isoformat(),
                    customer_label='Validation customer', objective='SQL fixture', budget_minor=1000, action=action,
                    stage='validation', reason='Explicit integration-test fixture, not a model call.',
                    restaurant_id=None, product_id=None, order_id=None, cart_total_minor=0,
                    decision_mode='ollama' if model else 'traffic', model='fixture' if model else None, source_kind='synthetic')

    def test_ordered_funnel_rejects_wrong_order_ties_and_expired_steps_without_counting_retries(self):
        run, rows = str(uuid4()), []
        at = datetime.now(timezone.utc) - timedelta(hours=2)
        paths = [(['session_started', 'open_product', 'add_to_cart', 'checkout'], [0, 1, 2, 3]),
                 (['session_started', 'open_product', 'abandon'], [0, 1, 2]),
                 (['session_started', 'add_to_cart', 'open_product', 'checkout'], [0, 1, 2, 3]),
                 (['session_started', 'open_product', 'add_to_cart', 'checkout'], [0, 0, 0, 0]),
                 (['session_started', 'open_product', 'add_to_cart', 'checkout'], [0, 1900, 1901, 1902]),
                 (['open_product'], [0])]
        for i, (actions, offsets) in enumerate(paths):
            customer, session = str(uuid4()), str(uuid4())
            rows.extend(self.activity(run, customer, session, action, at + timedelta(seconds=offset), model=i == 0 and action == 'checkout')
                        for action, offset in zip(actions, offsets))
        rows.append(dict(rows[1]))  # Same physical event resent.
        rows.append(self.activity(str(uuid4()), str(uuid4()), str(uuid4()), 'session_started', at))
        self.ch.execute('INSERT INTO delivery_atlas.customer_activity FORMAT JSONEachRow\n' + '\n'.join(map(json.dumps, rows)))
        data = Analytics(self.ch).journey(run)
        self.assertEqual([s['sessions'] for s in data['steps']], [5, 3, 1, 1])
        self.assertEqual((data['abandoned_sessions'], data['excluded_sessions']), (1, 1))
        self.assertEqual(sum(int(r['events']) for r in data['actions']), len(rows) - 2)
        ai, simulated = Analytics(self.ch).journey(run, 'ai'), Analytics(self.ch).journey(run, 'simulated')
        self.assertEqual([s['sessions'] for s in ai['steps']], [1, 1, 1, 1])
        self.assertEqual([s['sessions'] for s in simulated['steps']], [4, 2, 0, 0])
        self.assertTrue(all(q['rows_read'] > 0 for q in data['queries']))

    def test_empty_journey_is_distinct_from_a_zero_percent_conversion(self):
        data = Analytics(self.ch).journey(str(uuid4()))
        self.assertEqual(data['cohort_sessions'], 0)
        self.assertTrue(all(s['share_pct'] is None for s in data['steps']))
        self.assertFalse(Analytics(self.ch).journey(None)['available'])

    def test_live_comparisons_require_equal_answers_and_record_real_query_statistics(self):
        otto = Analytics(self.ch).benchmark('otto')
        self.assertTrue(otto['same_result'])
        self.assertEqual((otto['result_groups'], otto['logical_events']), (3, 3))
        run, session = str(uuid4()), str(uuid4())
        row = dict(schema_version=1, event_id=str(uuid4()), session_id=session,
                   event_time='2026-10-27T10:00:00Z', ingested_at='2026-10-27T10:00:01Z',
                   event_type='search', section='search', city_id='madrid', user_id=None,
                   restaurant_id=None, product_id=None, source='validation', source_kind='synthetic',
                   source_record_id=None, simulation_run_id=run)
        self.ch.execute('INSERT INTO delivery_atlas.app_events FORMAT JSONEachRow\n' + json.dumps(row) + '\n' + json.dumps(row))
        atlas = Analytics(self.ch).benchmark('atlas')
        self.assertTrue(atlas['same_result'])
        self.assertEqual(atlas['logical_events'], 1)
        self.assertIn('All runs', atlas['scope'])
        self.ch.execute('ALTER TABLE delivery.otto_daily_rollup DELETE WHERE 1 SETTINGS mutations_sync=2')
        wrong = Analytics(self.ch).benchmark('otto')
        self.assertFalse(wrong['same_result'])
        self.assertIsNone(wrong['ratio'])

    def test_every_historical_dashboard_uses_real_sql_and_honours_its_filter(self):
        expected = {'otto': ('events', 3), 'rees46': ('events', 2), 'eleme': ('samples', 1),
                    'glovo': ('products', 2), 'criteo': ('users', 2)}
        for dataset, (key, total) in expected.items():
            with self.subTest(dataset=dataset):
                data = Analytics(self.ch).historical(dataset)
                self.assertEqual(int(data['metrics'][key]), total)
                self.assertEqual(len(data['charts']), 3)
                self.assertTrue(all('elapsed_ms' in q for q in data['queries']))
        self.assertEqual(int(Analytics(self.ch).historical('rees46', period='201910')['metrics']['events']), 1)
        self.assertEqual(int(Analytics(self.ch).historical('glovo', country='ES', city='MAD')['metrics']['products']), 1)

    def test_storage_and_completed_queries_are_read_from_clickhouse_system_tables(self):
        self.raw('SYSTEM FLUSH LOGS')  # Test setup, never exposed by the public API.
        data = Analytics(self.ch).performance()
        self.assertTrue(data['version'].startswith('25.8.'))
        self.assertTrue(any(r['table'] == 'otto_archive' and int(r['physical_rows']) == 3 for r in data['tables']))
        self.assertTrue(data['log_available'])
        self.assertGreater(len(data['history']), 0)


if __name__ == '__main__':
    unittest.main()
