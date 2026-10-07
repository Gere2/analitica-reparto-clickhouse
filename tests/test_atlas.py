"""Meaningful retry, conflict, atomicity, queue and contract checks."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4
from atlas.contract import validate
from atlas.store import Store, Conflict, Full

def sample():
    return {'schema_version':1,'event_id':str(uuid4()),'session_id':str(uuid4()),
            'event_time':datetime.now(timezone.utc).isoformat(),'event_type':'search',
            'section':'search','city_id':'madrid','source':'unit-test','source_kind':'demo_live'}

class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(self.tmp.name+'/outbox.sqlite',max_pending=2)
        self.event=validate(sample())
    def tearDown(self):
        self.tmp.cleanup()
    def test_concurrent_retry_and_restart(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _: self.store.accept([self.event]), range(8)))
        self.assertEqual(sum(r['accepted'] for r in results),1)
        restored=Store(self.store.path)
        self.assertEqual(restored.accept([self.event])['duplicates'],1)
        self.assertEqual(restored.status()['pending'],1)
    def test_conflict_rolls_back_entire_batch(self):
        self.store.accept([self.event])
        bad=dict(self.event,city_id='barcelona')
        with self.assertRaises(Conflict):
            self.store.accept([validate(sample()),bad])
        self.assertEqual(self.store.status()['accepted'],1)
    def test_capacity_and_duplicates(self):
        self.store.accept([self.event,validate(sample())])
        self.assertEqual(self.store.accept([self.event])['duplicates'],1)
        with self.assertRaises(Full):
            self.store.accept([validate(sample())])
    def test_invalid_contract(self):
        for changed in [dict(sample(),schema_version=True),dict(sample(),event_type='paid'),
                        dict(sample(),event_time='2026-10-07T10:00:00'),
                        dict(sample(),event_type='cart_added'),dict(sample(),source_kind='synthetic')]:
            with self.assertRaises(ValueError):
                validate(changed)

if __name__=='__main__':
    unittest.main()
