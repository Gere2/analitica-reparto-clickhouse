import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from atlas.classroom import Classroom
from atlas.store import Store


class Sim:
    def __init__(self):
        self.state={'running':True,'mode':'customers','run_id':str(uuid4())}
        self.orders={}
        self.fail=False

    def snapshot(self):
        return dict(self.state)

    def checkout(self, body):
        if self.fail:
            self.orders[body['order_id']]=copy.deepcopy(body)
            self.fail=False
            raise OSError('Response lost')
        old=self.orders.setdefault(body['order_id'],copy.deepcopy(body))
        assert old==body
        return {'order_id':body['order_id'],'run_id':self.state['run_id'],'state':'queued'}


class CH:
    def query(self,sql,params=None):
        if 'demo_products' in sql:
            return [dict(product_id='bowl',restaurant_id='venue',product_name='Bowl',price_minor=1000)]
        return []


class ClassroomTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'queue.sqlite')
        self.sim=Sim()
        self.c=Classroom(self.store,self.sim,CH())
        self.room=self.c.manage('open')['room_id']
        self.body=dict(room_id=self.room,client_id=str(uuid4()),alias='Alex',product_id='bowl')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_retry_concurrency_and_metadata_restart(self):
        self.sim.fail=True
        with self.assertRaises(OSError):
            self.c.submit(self.body)
        with ThreadPoolExecutor(max_workers=8) as pool:
            orders=list(pool.map(lambda _:self.c.submit(self.body)['order_id'], range(8)))
        self.assertEqual(len(set(orders)),1)
        self.assertEqual(len(self.sim.orders),1)
        c=Classroom(self.store,self.sim,CH())
        self.assertEqual(c.submit(self.body)['state'],'already_accepted')
        snap=c.snapshot(self.room)
        self.assertEqual(snap['orders'][0]['alias'],'Alex')
        self.assertFalse(snap['orders'][0]['published'])

    def test_room_and_client_limits(self):
        self.c.submit(self.body)
        with self.assertRaises(ValueError):
            self.c.submit(dict(self.body,alias='Other'))
        with self.assertRaises(ValueError):
            self.c.submit(dict(self.body,client_id=str(uuid4()),product_id='unknown'))
        with self.assertRaises(ValueError):
            self.c.submit(dict(self.body,alias='<img onerror=alert(1)>'))
        self.c.manage('close')
        with self.assertRaises(LookupError):
            self.c.submit(self.body)
        self.assertFalse(self.c.snapshot(self.room)['open'])

    def test_capacity_and_expiry_keep_existing_receipts(self):
        self.c.submit(self.body)
        room=self.store.metadata('classroom')
        sample=next(iter(room['records'].values()))
        room['records'].update({str(uuid4()):dict(sample) for _ in range(99)})
        self.store.metadata('classroom',room)
        with self.assertRaises(ValueError):
            self.c.submit(dict(self.body,client_id=str(uuid4())))
        room['expires']=0
        self.store.metadata('classroom',room)
        with self.assertRaises(LookupError):
            self.c.submit(self.body)
        self.assertFalse(self.c.current()['open'])

    def test_new_run_and_expired_rooms_reject_writes(self):
        self.sim.state['run_id']=str(uuid4())
        with self.assertRaises(LookupError):
            self.c.submit(self.body)
        with self.assertRaises(LookupError):
            self.c.snapshot(str(uuid4()))

if __name__=='__main__':
    unittest.main()
