"""Bounded classroom room. Orders use the existing durable checkout pipeline."""
import re
import threading
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5


class Classroom:
    def __init__(self, store, simulator, ch):
        self.store, self.simulator, self.ch = store, simulator, ch
        self.lock = threading.RLock()
        self.cache = None

    def manage(self, action):
        with self.lock:
            if action == 'close':
                room = self.store.metadata('classroom')
                if room:
                    room['expires'] = 0
                    self.store.metadata('classroom', room)
                self.cache = None
                return {'open': False}
            if action != 'open':
                raise ValueError('Choose open or close.')
            sim = self.simulator.snapshot()
            if not sim.get('running') or sim.get('mode') != 'customers':
                raise LookupError('Start customers and delivery before opening the classroom.')
            room = dict(room_id=str(uuid4()), run_id=sim['run_id'],
                        expires=time.time() + 3600, records={})
            self.store.metadata('classroom', room)
            self.cache = None
            return dict(open=True, room_id=room['room_id'], expires=room['expires'])

    def current(self):
        room = self.store.metadata('classroom')
        if not room:
            return {'open': False}
        try:
            self.room(room['room_id'], write=True)
        except LookupError:
            return {'open': False}
        return dict(open=True, room_id=room['room_id'], expires=room['expires'])

    def room(self, room_id, write=False):
        room_id = str(UUID(room_id))
        room = self.store.metadata('classroom')
        if not room or room['room_id'] != room_id:
            raise LookupError('This classroom link is unavailable. Scan the current QR.')
        if write:
            sim = self.simulator.snapshot()
            if room['expires'] < time.time():
                raise LookupError('Ordering is closed for this classroom.')
            if not sim.get('running') or sim.get('run_id') != room['run_id']:
                raise LookupError('The delivery simulation is paused. Try again when the presenter resumes it.')
        return room

    def submit(self, body):
        if not isinstance(body, dict) or set(body) != {'room_id', 'client_id', 'alias', 'product_id'}:
            raise ValueError('Send room_id, client_id, alias and product_id.')
        client = str(UUID(body['client_id']))
        alias = body['alias']
        if not isinstance(alias, str) or not re.fullmatch(r"[\w .'-]{1,24}", alias) or not alias.strip():
            raise ValueError('Use a nickname of 1–24 letters, digits, spaces, dots or hyphens.')
        with self.lock:
            room = self.room(body['room_id'], write=True)
            record = room['records'].get(client)
            if record:
                if record['alias'] != alias.strip() or record['product_id'] != body['product_id']:
                    raise ValueError('You already have a classroom order on this device.')
                if record.get('accepted'):
                    return {'order_id': record['order_id'], 'run_id': room['run_id'], 'state': 'already_accepted'}
            else:
                if len(room['records']) >= 100:
                    raise ValueError('The classroom has reached its 100-order limit.')
                products = self.catalog()['products']
                product = next((p for p in products if p['product_id'] == body['product_id']), None)
                if product is None:
                    raise ValueError('Choose a dish from this classroom menu.')
                record = dict(alias=alias.strip(), product_id=product['product_id'],
                              product_name=product['product_name'], restaurant_id=product['restaurant_id'],
                              order_id=str(uuid5(UUID(room['room_id']), client)),
                              event_time=datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                              accepted=False)
                room['records'][client] = record
                # Reserve identity/time before checkout so retries keep the same event fingerprint.
                self.store.metadata('classroom', room)
            order_id = record['order_id']
            result = self.simulator.checkout(dict(order_id=order_id, customer_id=client,
                session_id=str(uuid5(UUID(order_id), 'session')),
                checkout_event_id=str(uuid5(UUID(order_id), 'checkout')), event_time=record['event_time'],
                restaurant_id=record['restaurant_id'], items=[dict(product_id=record['product_id'], quantity=1)]))
            record['accepted'] = True
            self.store.metadata('classroom', room)
            self.cache = None
            return result

    def catalog(self):
        return {'products': self.ch.query('SELECT product_id,restaurant_id,product_name,price_minor '
                                         'FROM delivery_atlas.demo_products FINAL ORDER BY product_id LIMIT 50')}

    def snapshot(self, room_id):
        with self.lock:
            room = self.room(room_id)
            if self.cache and self.cache[0] == room_id and time.monotonic() - self.cache[1] < 2:
                return self.cache[2]
            records = list(room['records'].values())
            orders = []
            if records:
                params = {'param_run': room['run_id'],
                          'param_ids': '[' + ','.join("'" + r['order_id'] + "'" for r in records) + ']'}
                orders = self.ch.query(
                    'SELECT order_id,courier_id,'
                    'status,dropoff_lat,dropoff_lon,toString(event_time) AS event_time '
                    'FROM delivery_atlas.order_latest WHERE simulation_run_id={run:UUID} '
                    'AND order_id IN {ids:Array(UUID)}', params)
            published = {o['order_id']: o for o in orders}
            rows = [dict(alias=r['alias'], product_name=r['product_name'], order_id=r['order_id'],
                         **{k:v for k,v in published.get(r['order_id'], {}).items() if k != 'order_id'},
                         published=r['order_id'] in published) for r in records]
            result = dict(room_id=room_id, run_id=room['run_id'], expires=room['expires'],
                          open=room['expires'] > time.time() and self.simulator.snapshot().get('running', False)
                               and self.simulator.snapshot().get('run_id') == room['run_id'],
                          orders=rows, **self.catalog())
            self.cache = (room_id, time.monotonic(), result)
            return result
