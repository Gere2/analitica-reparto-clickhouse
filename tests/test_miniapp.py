"""Miniapp checkout: server-side prices, idempotent retries and delivery of the same order."""
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from atlas.commerce import CommerceEngine, MANUAL_SOURCE
from atlas.server import make_handler
from atlas.simulation import Simulator
from atlas.store import Store

WEB = Path(__file__).resolve().parents[1] / 'web'


def catalog():
    return {'restaurants': [
                {'restaurant_id': 'shop', 'name': 'Casa de prueba', 'city_id': 'madrid', 'latitude': 40.415, 'longitude': -3.704},
                {'restaurant_id': 'other', 'name': 'Otra casa', 'city_id': 'madrid', 'latitude': 40.416, 'longitude': -3.705}],
            'products': [
                {'product_id': 'meal', 'restaurant_id': 'shop', 'product_name': 'Menú ficticio', 'price_minor': 900},
                {'product_id': 'salad', 'restaurant_id': 'shop', 'product_name': 'Ensalada', 'price_minor': 650},
                {'product_id': 'foreign', 'restaurant_id': 'other', 'product_name': 'Ajeno', 'price_minor': 700}]}


def request(**overrides):
    body = {'order_id': str(uuid4()), 'customer_id': str(uuid4()), 'session_id': str(uuid4()),
            'checkout_event_id': str(uuid4()), 'event_time': datetime.now(timezone.utc).isoformat(),
            'restaurant_id': 'shop', 'items': [{'product_id': 'meal', 'quantity': 2}, {'product_id': 'salad', 'quantity': 1}]}
    body.update(overrides)
    return body


class ManualCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.at = datetime.now(timezone.utc)
        self.engine = CommerceEngine(str(uuid4()), self.at, 1, 1, 42, catalog(), 'policy')
        self.engine.advance(self.at)

    def test_links_click_purchase_and_order_with_catalog_prices(self):
        body = request()
        nav, purchase, order = self.engine.manual_checkout(body, self.at)
        self.assertEqual((nav['event_type'], nav['source'], nav['source_kind']), ('order_submitted', MANUAL_SOURCE, 'demo_live'))
        self.assertEqual(nav['order_id'], body['order_id'])
        self.assertEqual(purchase['checkout_event_id'], nav['event_id'])
        self.assertEqual((purchase['source_kind'], purchase['decision_mode']), ('demo_live', 'manual'))
        self.assertEqual(purchase['items'], [['meal', 2, 900], ['salad', 1, 650]])
        self.assertEqual(purchase['amount_minor'], 2450)
        self.assertEqual((order['_stream'], order['order_id'], order['amount_minor'], order['source_kind']),
                         ('order_events', body['order_id'], 2450, 'synthetic'))

    def test_client_cannot_set_price_or_mix_restaurants(self):
        bad = [request(items=[{'product_id': 'meal', 'quantity': 1, 'price_minor': 1}]),
               request(items=[{'product_id': 'foreign', 'quantity': 1}]),
               request(items=[{'product_id': 'meal', 'quantity': 0}]),
               request(items=[{'product_id': 'meal', 'quantity': 1}, {'product_id': 'meal', 'quantity': 1}]),
               request(items=[]), request(restaurant_id='nope'), request(order_id='no-uuid'),
               dict(request(), amount_minor=1)]
        for body in bad:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.engine.manual_checkout(body, self.at)
        self.assertFalse(self.engine.orders)

    def test_retry_is_idempotent_and_reused_order_id_rejected(self):
        body = request()
        self.assertEqual(len(self.engine.manual_checkout(body, self.at)), 3)
        self.assertEqual(self.engine.manual_checkout(body, self.at), [])
        with self.assertRaises(ValueError):
            self.engine.manual_checkout(dict(body, checkout_event_id=str(uuid4())), self.at)
        self.assertEqual(len(self.engine.orders), 1)

    def test_same_courier_delivers_manual_order_without_touching_ai_customers(self):
        body = request()
        self.engine.manual_checkout(body, self.at)
        assigned = self.engine.advance(self.at + timedelta(seconds=10))
        gps = next(r for r in assigned if r['_stream'] == 'courier_positions')
        self.assertEqual(gps['order_id'], body['order_id'])
        final = self.engine.advance(self.at + timedelta(seconds=110))
        delivered = next(r for r in final if r['_stream'] == 'order_events' and r['status'] == 'delivered')
        self.assertEqual(delivered['order_id'], body['order_id'])
        self.assertFalse(any(r['_stream'] == 'customer_activity' and r['action'] == 'delivery_completed' for r in final))


class FakeCH:
    def query(self, sql, params=None):
        return [{'result': 1}]


class FakeRuntime:
    """Wraps a real engine; mirrors CustomerRuntime.manual_checkout acceptance."""
    def __init__(self, store):
        self.store = store
        self.engine = CommerceEngine(str(uuid4()), datetime.now(timezone.utc), 1, 1, 42, catalog(), 'policy')

    def manual_checkout(self, body):
        rows = self.engine.manual_checkout(body, datetime.now(timezone.utc))
        if rows:
            self.store.accept(rows)
        order = self.engine.orders[body['order_id']]
        return {'state': 'queued' if rows else 'already_accepted', 'run_id': self.engine.run_id,
                'order_id': order['id'], 'amount_minor': order['amount'], 'currency': 'EUR'}


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name + '/outbox.sqlite')
        self.simulator = Simulator(self.store)
        publisher = type('P', (), {'error': None, 'phase': 'idle', 'phase_started': 0, 'last_batch': 0, 'last_publish_seconds': None})()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.store, FakeCH(), publisher, self.simulator))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.store.close(); self.tmp.cleanup()

    def post(self, path, body):
        try:
            with urlopen(Request(self.base + path, json.dumps(body).encode(), {'Content-Type': 'application/json'})) as r:
                return r.status, json.loads(r.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_without_customer_run_nothing_is_created(self):
        status, data = self.post('/api/checkout', request())
        self.assertEqual((status, data['code']), (409, 'no_customer_run'))
        self.assertEqual(self.store.status()['accepted'], 0)

    def test_checkout_queued_then_retry_returns_200(self):
        self.simulator.customer_runtime = FakeRuntime(self.store)
        body = request()
        status, data = self.post('/api/checkout', body)
        self.assertEqual((status, data['state'], data['amount_minor']), (202, 'queued', 2450))
        status, data = self.post('/api/checkout', body)
        self.assertEqual((status, data['state']), (200, 'already_accepted'))
        self.assertEqual(self.store.status()['accepted'], 3)
        status, _ = self.post('/api/checkout', request(items=[{'product_id': 'foreign', 'quantity': 1}]))
        self.assertEqual(status, 400)

    def test_miniapp_events_follow_contract(self):
        session = str(uuid4())
        events = [{'schema_version': 1, 'event_id': str(uuid4()), 'session_id': session,
                   'event_time': datetime.now(timezone.utc).isoformat(), 'event_type': kind, 'section': section,
                   'city_id': 'madrid', 'source': MANUAL_SOURCE, 'source_kind': 'demo_live', **extra}
                  for kind, section, extra in [('search', 'search', {}), ('filter_applied', 'search', {}),
                      ('restaurant_opened', 'restaurants', {'restaurant_id': 'shop'}),
                      ('product_opened', 'menu', {'restaurant_id': 'shop', 'product_id': 'meal'}),
                      ('cart_added', 'cart', {'restaurant_id': 'shop', 'product_id': 'meal'}),
                      ('cart_removed', 'cart', {'restaurant_id': 'shop', 'product_id': 'meal'}),
                      ('session_abandoned', 'session', {})]]
        status, data = self.post('/api/events', {'events': events})
        self.assertEqual((status, data['accepted']), (202, 7))

    def test_miniapp_files_are_served(self):
        for name in ('delivery.html', 'delivery.js', 'delivery.css'):
            self.assertTrue((WEB / name).is_file(), name)
            with urlopen(self.base + '/' + name) as r:
                self.assertEqual(r.status, 200)


if __name__ == '__main__':
    unittest.main()
