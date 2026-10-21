"""Data views: AI agents and simulated customers counted apart, and the downloaded datasets summary."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from atlas.clickhouse import ClickHouse
from atlas.commerce import CommerceEngine
from atlas.server import Publisher
from atlas.share import canonical_path
from atlas.store import Store

CATALOG = {'restaurants': [
               {'restaurant_id': 'shop', 'name': 'Casa de prueba', 'city_id': 'madrid', 'latitude': 40.415, 'longitude': -3.704},
               {'restaurant_id': 'other', 'name': 'Otra casa', 'city_id': 'madrid', 'latitude': 40.416, 'longitude': -3.705}],
           'products': [
               {'product_id': 'meal', 'restaurant_id': 'shop', 'product_name': 'Menú ficticio', 'price_minor': 900},
               {'product_id': 'foreign', 'restaurant_id': 'other', 'product_name': 'Ajeno', 'price_minor': 700}]}


class StubClickHouse(ClickHouse):
    """Answers the datasets queries from memory and records every SQL statement."""
    def __init__(self, loaded):
        super().__init__()
        self.loaded, self.statements = loaded, []

    def result(self, sql, params=None):
        self.statements.append(sql)
        if 'system.tables' in sql:
            data = [{'name': name, 'total_rows': str(rows)} for name, rows in self.loaded.items()]
        elif 'now64' in sql:
            data = [{'at': '2026-10-21 15:00:00.000'}]
        elif 'criteo_uplift' in sql:
            data = [{'treatment': 0, 'users': '10'}, {'treatment': 1, 'users': '30'}]
        else:
            data = [{'country_code': 'ES', 'products': '5', 'stores': '2', 'madrid_products': '3'}]
        return {'data': data, 'statistics': {'elapsed': 0.0123, 'rows_read': 40}}


class DatasetsSummaryTests(unittest.TestCase):
    def test_missing_or_empty_datasets_are_reported_without_querying_them(self):
        for loaded in ({}, {'criteo_uplift': 0, 'glovo_products': 0}):
            with self.subTest(loaded=loaded):
                ch = StubClickHouse(loaded)
                data = ch.datasets()
                self.assertIsNone(data['criteo'])
                self.assertIsNone(data['glovo'])
                self.assertFalse(any('FROM delivery.' in sql for sql in ch.statements))

    def test_loaded_datasets_carry_clickhouse_timing(self):
        data = StubClickHouse({'criteo_uplift': 40, 'glovo_products': 5}).datasets()
        self.assertEqual([row['treatment'] for row in data['criteo']['rows']], [0, 1])
        self.assertEqual((data['criteo']['elapsed_ms'], data['criteo']['rows_read']), (12.3, 40))
        self.assertEqual(data['glovo']['rows'][0]['country_code'], 'ES')
        self.assertEqual(data['queried_at'], '2026-10-21 15:00:00.000')

    def test_shared_gateway_allows_the_datasets_read_without_parameters(self):
        self.assertEqual(canonical_path('/api/datasets'), ('datasets', '/api/datasets'))
        with self.assertRaises(ValueError):
            canonical_path('/api/datasets?table=criteo_uplift')


def buy(engine, customer_id, at):
    rows = []
    for action in ('search', 'open_restaurant', 'open_product', 'add_to_cart', 'checkout'):
        context = engine.context(customer_id, at)
        rows += engine.decide(customer_id, context['revision'], {'action': action, 'choice': 0, 'reason': 'Test path.'}, at)
    return rows


@unittest.skipUnless(os.environ.get('ATLAS_TEST_CLICKHOUSE_URL'), 'Requires a disposable ClickHouse instance')
class CustomerTypeIntegrationTests(unittest.TestCase):
    def test_downloaded_dataset_queries_and_timing_use_real_clickhouse(self):
        ch=ClickHouse();ch.url=os.environ['ATLAS_TEST_CLICKHOUSE_URL'].rstrip('/')
        database='test_pr78_'+uuid4().hex
        execute=ch.execute
        execute('CREATE DATABASE '+database)
        def isolated(sql,params=None):
            return execute(sql.replace("database='delivery'",f"database='{database}'").replace('delivery.',database+'.'),params)
        try:
            with patch.object(ch,'execute',side_effect=isolated):
                schema=(Path(__file__).resolve().parents[1]/'sql/criteo.sql').read_text()
                ch.execute(schema)
                zeros=','.join(['0']*12)
                ch.execute(f'INSERT INTO delivery.criteo_uplift VALUES ({zeros},0,0,1,0),({zeros},1,1,1,1)')
                ch.execute('CREATE TABLE delivery.glovo_products (source_row UInt64,country_code String,city_code String,store_name String) ENGINE=MergeTree ORDER BY source_row')
                ch.execute("INSERT INTO delivery.glovo_products VALUES (1,'ES','MAD','Shop'),(2,'ES','MAD','Shop'),(3,'FR','PAR','Other')")
                data=ch.datasets()
                groups={int(r['treatment']):r for r in data['criteo']['rows']}
                self.assertEqual((int(groups[0]['users']),float(groups[0]['conversion_rate'])),(1,0))
                self.assertEqual((int(groups[1]['users']),float(groups[1]['conversion_rate'])),(1,1))
                countries={r['country_code']:r for r in data['glovo']['rows']}
                self.assertEqual((int(countries['ES']['products']),int(countries['ES']['stores']),int(countries['ES']['madrid_products'])),(2,1,2))
                for name in ('criteo','glovo'):
                    self.assertGreater(data[name]['rows_read'],0)
                    self.assertGreaterEqual(data[name]['elapsed_ms'],0)
        finally:
            execute('DROP DATABASE IF EXISTS '+database)

    def test_ai_agents_and_simulated_customers_are_counted_apart(self):
        ch = ClickHouse()
        ch.url = os.environ['ATLAS_TEST_CLICKHOUSE_URL'].rstrip('/')
        ch.init()
        at = datetime.now(timezone.utc) - timedelta(seconds=60)
        # In a hybrid run the first three customers are AI agents and the rest use the traffic simulator.
        engine = CommerceEngine(str(uuid4()), at, 3, 4, 42, CATALOG, 'hybrid')
        agent, _, _, simulated = list(engine.customers)
        manual = {'order_id': str(uuid4()), 'customer_id': str(uuid4()), 'session_id': str(uuid4()),
                  'checkout_event_id': str(uuid4()), 'event_time': at.isoformat(),
                  'restaurant_id': 'shop', 'items': [{'product_id': 'meal', 'quantity': 1}]}
        rows = engine.advance(at) + buy(engine, agent, at) + buy(engine, simulated, at) + engine.manual_checkout(manual, at)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp + '/outbox.sqlite')
            try:
                store.accept(rows)
                Publisher(store, ch).once()
                self.assertEqual(store.status()['pending'], 0)
                data = ch.operations(engine.run_id)
            finally:
                store.close()
        # Manual mini-app orders are shown with the simulated customers.
        self.assertEqual(data['metrics_by_kind']['ai']['orders'], 1)
        self.assertEqual(data['metrics_by_kind']['simulated']['orders'], 2)
        self.assertEqual(data['metrics']['orders'], 3)
        agents, others = data['customer_metrics_by_kind']['ai'], data['customer_metrics_by_kind']['simulated']
        self.assertEqual((agents['sessions'], agents['checkouts'], agents['model_decisions']), (1, 1, 5))
        # The two AI agents without a model decision yet still count as simulated sessions.
        self.assertEqual((others['sessions'], others['checkouts'], others['model_decisions']), (3, 1, 0))
        self.assertEqual(data['customer_metrics']['sessions'], 4)
        self.assertEqual(sum(a['decision_mode'] == 'ollama' for a in data['activity']), 5)


if __name__ == '__main__':
    unittest.main()
